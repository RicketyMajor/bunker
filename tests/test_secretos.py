"""Check that no secret is committed and that a 500 cannot hand one over. Runs in container:

    docker compose exec -T web python -m tests.test_secretos

Measured 2026-08-22 by `/security-review`, all five findings verified by executing. The
repository `github.com/RicketyMajor/bunker` answers HTTP 200 unauthenticated — it is PUBLIC —
and two tracked files carried literal secrets: `POSTGRES_PASSWORD` in `docker-compose.yml`
and `SECRET_KEY` in `bunker_core/settings.py`. With `5436:5432` bound to `0.0.0.0`, that
password opened the whole database as `admin` from the LAN, bypassing Django entirely.

The subtle one is `DEBUG`. The finding said a 500 returns the `settings` dictionary and with
it every API key. **That half is wrong and the inversion proved it**: Django masks 24 setting
values, `SECRET_KEY` among them, and the API keys are read from `os.environ` inside views, so
they were never in `settings` to begin with. What Django does NOT mask is the local variables
of each frame — and `_reject_if_bad_token` (`bunker_core/views.py:43`) holds
`BUNKER_BACKUP_TOKEN` in exactly such a local. Measured, DEBUG=True, 49.888 bytes:

    secreto_local | 'lbYZ9u-sZ8jWPT8EhlyqjkkwJ9QFmTOeoI5OG09u4jY'

So the consequence the backlog described is real and the mechanism it named is not. This
check guards the consequence.

It reads the tracked files from /app (bind-mounted) and needs no fixtures, so an empty
database cannot satisfy it.
"""
import os
import re
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.conf import settings  # noqa: E402

_checks = 0

# The two values that were published. They are burned into the git history for ever, so the
# point is not that they stay out of HEAD — it is that they never come back as live config.
_CLAVE_PUBLICADA = 'django-insecure-r57@yay8wlt5gifn*x9x5@k!*#&)tdhd*)f!&=qi&5#^ulj$^h'
_PASSWORD_PUBLICADA = 'supersecret'

# A line that assigns a secret. The name is spelled three ways across the two files: compose
# uses POSTGRES_PASSWORD, settings.py uses SECRET_KEY, and Django's DATABASES dict uses the bare
# key 'PASSWORD'. The previous version listed only the first two, so the whole DATABASES block
# was invisible to it and `'PASSWORD': 'supersecret'` would have passed.
_ASIGNACION = re.compile(
    r"""^[ \t]*-?[ \t]*['"]?(POSTGRES_PASSWORD|SECRET_KEY|PASSWORD)['"]?[ \t]*[=:][ \t]*"""
    r"""(.+?),?[ \t]*(?:\#.*)?$""",
    re.M)

# The only value shapes a secret may take, matched against the WHOLE value. This is an
# ALLOWLIST on purpose. The previous version was a blocklist of safe-looking prefixes
# — `(?!\$\{)(?!os\.environ)` — tested against how the value STARTED, and it was wrong in both
# directions: everything after an allowed prefix was invisible, so a literal default inside
# os.environ.get(...) passed; and any spelling not on the list, `os.getenv` among them, was
# reported as a violation. An allowlist fails closed, which is the direction a secrets guard
# should fail.
#
# An EMPTY default is allowed: it cannot authenticate, and settings.py:39 turns it into an
# ImproperlyConfigured. A non-empty one is a working secret in a public file.
_VALOR_SEGURO = re.compile(
    r"""\A(?:
          \$\{[A-Za-z_]\w*(?::\?[^}]*|:?-)?\}       # ${VAR}, ${VAR:?mensaje}, ${VAR:-}
                                                  # NO ${VAR:-literal}: en compose ese
                                                  # texto es un VALOR, no un mensaje.
        | os\.environ\[[^\]]+\]                      # os.environ['CLAVE']
        | os\.(?:environ\.get|getenv)\([^,)]+(?:,[ \t]*(?:\'\'|""))?\)   # get('CLAVE') / get('CLAVE', '')
        )(?:\.strip\(\))?\Z""",
    re.X)

# Variables whose absence must genuinely stop the stack, and so may use compose's `${VAR:?}`.
# That marker aborts the interpolation of the WHOLE FILE, so `up`, `ps`, `logs`, `down` and the
# 18 `docker compose exec` of cli/doctor.py:130 die with it — not just the service that reads
# the variable. DISCOGS_API_KEY was on this list and should not have been: the stack runs fine
# without it, because scraper/strategies/music/discogs.js:7 skips its strategy when it is empty.
_REQUERIDAS_EN_COMPOSE = {'POSTGRES_PASSWORD'}


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


_COMPOSE = settings.BASE_DIR / 'docker-compose.yml'
_SETTINGS = settings.BASE_DIR / 'bunker_core' / 'settings.py'


def test_ningun_secreto_literal_en_ficheros_rastreados():
    """docker-compose.yml and settings.py must reach the secrets through the environment."""
    for ruta in (_COMPOSE, _SETTINGS):
        texto = ruta.read_text(encoding='utf-8')
        asignaciones = [(m.group(1), m.group(2)) for m in _ASIGNACION.finditer(texto)]
        # Non-vacuity: a pattern that matches nothing reports "no literals" for ever. Both
        # files assign at least one secret, so zero matches means the regex broke, not that
        # the file is clean.
        check(bool(asignaciones),
              f"{ruta.name}: la sonda VE asignaciones de secreto ({len(asignaciones)})")
        hallazgos = [f"{n} = {v}" for n, v in asignaciones if not _VALOR_SEGURO.match(v)]
        check(not hallazgos,
              f"{ruta.name} no asigna secretos literales; encontrado: {hallazgos}")
        for publicado, nombre in ((_PASSWORD_PUBLICADA, 'la contraseña publicada'),
                                  (_CLAVE_PUBLICADA, 'la SECRET_KEY publicada')):
            check(publicado not in texto, f"{ruta.name} no contiene {nombre}")


def test_compose_no_exige_variables_opcionales():
    """`${VAR:?}` aborts the interpolation of the whole file, not just its own service.

    Measured 2026-08-23: with `${DISCOGS_API_KEY:?falta en .env}` on the scraper-music service,
    `DISCOGS_API_KEY= docker compose ps` exited 1 — and so did every other subcommand, plus the
    18 `docker compose exec` that cli/doctor.py:130 makes. A fresh clone could not boot the
    stack because an OPTIONAL scraper key was missing.
    """
    # SIN LAS LINEAS DE COMENTARIO. La sonda leia el fichero entero como texto, asi que un
    # comentario que CITA un marcador contaba como si lo usara: el 2026-08-31, un comentario que
    # explicaba por que NO se usa `${DISCOGS_API_KEY:?falta en .env}` puso la suite en rojo y
    # acuso a una linea de configuracion que no existe. Se descartan solo las lineas cuyo primer
    # caracter no blanco es `#` — un comentario al final de una linea de configuracion se sigue
    # mirando, que es el lado seguro: un `:?` de verdad JAMAS vive dentro de un comentario, asi
    # que esto no puede perder ninguno.
    texto = _COMPOSE.read_text(encoding='utf-8')
    configuracion = '\n'.join(l for l in texto.splitlines() if not l.lstrip().startswith('#'))
    exigidas = set(re.findall(r'\$\{([A-Za-z_]\w*):\?', configuracion))
    check(bool(exigidas), f"la sonda VE marcadores ${{VAR:?}} en compose ({exigidas})")
    check(exigidas <= _REQUERIDAS_EN_COMPOSE,
          f"sólo las variables sin las que el stack no arranca usan ${{VAR:?}}; "
          f"de más: {sorted(exigidas - _REQUERIDAS_EN_COMPOSE)}")


def test_la_secret_key_viva_no_es_la_publicada():
    check(bool(settings.SECRET_KEY), "SECRET_KEY no está vacía")
    check(settings.SECRET_KEY != _CLAVE_PUBLICADA,
          "SECRET_KEY viva NO es la que está en el repositorio público")
    check(not settings.SECRET_KEY.startswith('django-insecure-'),
          "SECRET_KEY no es una generada por startproject")


def test_la_contrasena_viva_de_postgres_no_es_la_publicada():
    """The half that was missing, and it is the half that decides.

    The two published constants had exactly complementary coverage: _CLAVE_PUBLICADA was only
    ever compared against LIVE config, _PASSWORD_PUBLICADA only ever searched for as TEXT in
    the tracked files. So the file could report every check OK while `docker compose config`
    printed `supersecret` — which is precisely what happened between 2026-08-22 and today.
    Rotating .env alone does NOT fix this: the postgres image applies POSTGRES_PASSWORD only
    when it creates the volume. It needs, inside the `db` container,

        ALTER USER admin WITH PASSWORD '<nueva>';

    and only then the new value in .env plus `docker compose up -d --force-recreate`.
    """
    viva = settings.DATABASES['default']['PASSWORD']
    check(bool(viva), "la contraseña de Postgres no está vacía")
    check(viva != _PASSWORD_PUBLICADA,
          "la contraseña VIVA de Postgres NO es la que está en el repositorio público")


def test_debug_apagado_y_allowed_hosts_cerrado():
    check(settings.DEBUG is False, "DEBUG está apagado")
    check('*' not in settings.ALLOWED_HOSTS,
          f"ALLOWED_HOSTS no es un comodín; vale {settings.ALLOWED_HOSTS}")


def test_un_500_no_entrega_una_variable_local():
    """The consequence, not the mechanism: a crash must not print frame locals.

    Fires a real request through Django's exception handling with a view that holds a secret
    in a local, exactly like `_reject_if_bad_token` does. With DEBUG=True this same probe
    returns ~49 KB containing the value; the assertion below is what makes it non-vacuous.
    """
    import logging
    import sys
    import types

    from django.test import Client, override_settings
    from django.urls import path

    centinela = 'CENTINELA-e3f19a7c-no-debe-salir-nunca'

    def revienta(request):
        token_en_una_local = centinela      # noqa: F841 — es el objeto de la prueba
        raise RuntimeError('500 fabricado por tests.test_secretos')

    modulo = types.ModuleType('_urlconf_test_secretos')
    modulo.urlpatterns = [path('boom/', revienta)]
    sys.modules['_urlconf_test_secretos'] = modulo

    # Both of these used to leak. `logging.disable(NOTSET)` restores "nothing disabled", which
    # is not the same as restoring the previous level, and the fabricated urlconf stayed in
    # `sys.modules` for the life of the process. Harmless while this file is a standalone
    # script; it stops being harmless the day `cli/doctor.py` runs the checks in one process.
    nivel_previo = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with override_settings(ROOT_URLCONF='_urlconf_test_secretos'):
            respuesta = Client(raise_request_exception=False).get('/boom/')
            cuerpo = respuesta.content.decode('utf-8', 'replace')
    finally:
        logging.disable(nivel_previo)
        sys.modules.pop('_urlconf_test_secretos', None)

    check(respuesta.status_code == 500, "la vista de prueba devuelve 500")
    check(centinela not in cuerpo,
          f"un 500 NO entrega la local del frame ({len(cuerpo)} bytes devueltos)")
    check('Traceback' not in cuerpo, "un 500 NO entrega la traza")


def test_un_origen_publico_sin_esquema_falla_ruidosamente():
    """A `BUNKER_PUBLIC_ORIGIN` with no scheme must abort, not be dropped in silence.

    `urlparse('bunker.ts.net').hostname` is None -- the whole value lands in `path` -- so the
    `if _public_host` that guards the ALLOWED_HOSTS append skipped it without a word, and the
    failure surfaced much later as a CSRF `(4_0.E001)`, pointing whoever was debugging a 400
    from the phone at the wrong setting. Both directions are asserted: a scheme-less value
    raises, and a proper one still reaches ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS -- a guard
    that rejected everything would pass the first half alone.
    """
    import subprocess
    guion = (
        "import django, os;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE','bunker_core.settings');"
        "django.setup();"
        "from django.conf import settings;"
        "print('HOSTS', settings.ALLOWED_HOSTS);"
        "print('CSRF', settings.CSRF_TRUSTED_ORIGINS[-1])"
    )

    # Both spellings of "no scheme". `//host` is the one a hostname test misses: urlparse
    # DOES give it a hostname, so a guard written as `if not hostname` passes it through, and
    # it lands in CSRF_TRUSTED_ORIGINS in exactly the shape Django rejects with (4_0.E001) --
    # the late failure the guard exists to prevent. Found by review, verified by running.
    for malo in ('bunker.tail834684.ts.net', '//bunker.tail834684.ts.net'):
        sin = subprocess.run([sys.executable, '-c', guion], capture_output=True, text=True,
                             env={**os.environ, 'BUNKER_PUBLIC_ORIGIN': malo})
        check(sin.returncode != 0 and 'ImproperlyConfigured' in sin.stderr,
              f"'{malo}' aborta el arranque (salio {sin.returncode})")
        check('debe empezar por http' in sin.stderr,
              f"y el mensaje de '{malo}' nombra la causa, no un sintoma de CSRF")

    con = subprocess.run([sys.executable, '-c', guion], capture_output=True, text=True,
                         env={**os.environ,
                              'BUNKER_PUBLIC_ORIGIN': 'https://bunker.tail834684.ts.net'})
    check(con.returncode == 0 and 'bunker.tail834684.ts.net' in con.stdout,
          f"y uno CON esquema sigue llegando a ALLOWED_HOSTS (salio {con.returncode})")


def run_tests():
    print("Comprobando secretos y superficie de error…")
    test_ningun_secreto_literal_en_ficheros_rastreados()
    test_compose_no_exige_variables_opcionales()
    test_la_secret_key_viva_no_es_la_publicada()
    test_la_contrasena_viva_de_postgres_no_es_la_publicada()
    test_debug_apagado_y_allowed_hosts_cerrado()
    test_un_500_no_entrega_una_variable_local()
    test_un_origen_publico_sin_esquema_falla_ruidosamente()
    print(f"\n{_checks} comprobaciones OK.")


if __name__ == '__main__':
    run_tests()
