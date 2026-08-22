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

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.conf import settings  # noqa: E402

_checks = 0

# The two values that were published. They are burned into the git history for ever, so the
# point is not that they stay out of HEAD — it is that they never come back as live config.
_CLAVE_PUBLICADA = 'django-insecure-r57@yay8wlt5gifn*x9x5@k!*#&)tdhd*)f!&=qi&5#^ulj$^h'
_PASSWORD_PUBLICADA = 'supersecret'

# Assignments of a secret to a literal, as opposed to ${VAR} or os.environ.get(...).
_LITERAL = re.compile(
    r'^\s*-?\s*(POSTGRES_PASSWORD|SECRET_KEY)\s*[=:]\s*(?!\$\{)(?!os\.environ)'
    r'[\'"]?([^\'"\s$][^\'"\n]*)',
    re.M)


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def test_ningun_secreto_literal_en_ficheros_rastreados():
    """docker-compose.yml and settings.py must reach the secrets through the environment."""
    for ruta in ('/app/docker-compose.yml', '/app/bunker_core/settings.py'):
        with open(ruta, encoding='utf-8') as f:
            texto = f.read()
        hallazgos = [m.group(0).strip() for m in _LITERAL.finditer(texto)]
        check(not hallazgos, f"{ruta} no asigna secretos literales; encontrado: {hallazgos}")
        check(_PASSWORD_PUBLICADA not in texto,
              f"{ruta} no contiene la contraseña publicada")


def test_la_secret_key_viva_no_es_la_publicada():
    check(bool(settings.SECRET_KEY), "SECRET_KEY no está vacía")
    check(settings.SECRET_KEY != _CLAVE_PUBLICADA,
          "SECRET_KEY viva NO es la que está en el repositorio público")
    check(not settings.SECRET_KEY.startswith('django-insecure-'),
          "SECRET_KEY no es una generada por startproject")


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

    logging.disable(logging.CRITICAL)
    try:
        with override_settings(ROOT_URLCONF='_urlconf_test_secretos'):
            respuesta = Client(raise_request_exception=False).get('/boom/')
            cuerpo = respuesta.content.decode('utf-8', 'replace')
    finally:
        logging.disable(logging.NOTSET)

    check(respuesta.status_code == 500, "la vista de prueba devuelve 500")
    check(centinela not in cuerpo,
          f"un 500 NO entrega la local del frame ({len(cuerpo)} bytes devueltos)")
    check('Traceback' not in cuerpo, "un 500 NO entrega la traza")


def run_tests():
    print("Comprobando secretos y superficie de error…")
    test_ningun_secreto_literal_en_ficheros_rastreados()
    test_la_secret_key_viva_no_es_la_publicada()
    test_debug_apagado_y_allowed_hosts_cerrado()
    test_un_500_no_entrega_una_variable_local()
    print(f"\n{_checks} comprobaciones OK.")


if __name__ == '__main__':
    run_tests()
