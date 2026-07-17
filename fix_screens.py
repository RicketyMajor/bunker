import sys

# Read the base screens.py
with open('cli/tui/screens.py', 'r') as f:
    content = f.read()

# Find the start of BunkerLauncherScreen
old_start = content.find('class BunkerLauncherScreen(Screen):')
if old_start == -1:
    print('ERROR: Could not find BunkerLauncherScreen in screens.py')
    sys.exit(1)

# Keep the content before BunkerLauncherScreen
base_content = content[:old_start]

# Read the scratch new_launcher.py
with open('/home/alonso/.gemini/antigravity/brain/3842c717-a77c-4afc-a346-c29dc38c65ef/scratch/new_launcher.py', 'r') as f:
    new_class = f.read()

# Make the gruvbox adjustments to the new class
new_logo = '''    LOGO = (
        "[$success]██████╗  ██╗   ██╗ ███╗   ██╗ ██╗  ██╗ ███████╗ ██████╗ [/]\\n"
        "[$success]██╔══██╗ ██║   ██║ ████╗  ██║ ██║ ██╔╝ ██╔════╝ ██╔══██╗[/]\\n"
        "[$success]██████╔╝ ██║   ██║ ██╔██╗ ██║ █████╔╝  █████╗   ██████╔╝[/]\\n"
        "[$success]██╔══██╗ ██║   ██║ ██║╚██╗██║ ██╔═██╗  ██╔══╝   ██╔══██╗[/]\\n"
        "[$success]██████╔╝ ╚██████╔╝ ██║ ╚████║ ██║  ██╗ ███████╗ ██║  ██║[/]\\n"
        "[$success]╚═════╝   ╚═════╝  ╚═╝  ╚═══╝ ╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═╝[/]"
    )'''

# Replace the hardcoded cyberpunk logo
cyberpunk_logo_start = new_class.find('    LOGO = (')
cyberpunk_logo_end = new_class.find(')', cyberpunk_logo_start) + 1
new_class = new_class[:cyberpunk_logo_start] + new_logo + new_class[cyberpunk_logo_end:]

# Replace the hardcoded colors in CSS with Textual theme variables
new_class = new_class.replace('background: #0a0a0a;', '') # Let app.py handle background
new_class = new_class.replace('background: #111111;', 'background: $surface;')
new_class = new_class.replace('background: #0d1117;', 'background: $surface;')

# Text colors
new_class = new_class.replace('color: #00ff41;', 'color: $success;')
new_class = new_class.replace('color: #00e5ff;', 'color: $accent;')
new_class = new_class.replace('color: #ffb000;', 'color: $warning;')
new_class = new_class.replace('color: #555555;', 'color: $text-muted;')
new_class = new_class.replace('color: #888888;', 'color: $text-muted;')
new_class = new_class.replace('color: #c0c0c0;', 'color: $text;')

# Borders
new_class = new_class.replace('border: tall #00e5ff;', 'border: tall $accent;')
new_class = new_class.replace('border: tall #1a3a4a;', 'border: tall $primary;')
new_class = new_class.replace('border: tall #8b5cf6;', 'border: tall $primary;')
new_class = new_class.replace('border: tall #00ff41;', 'border: tall $success;')

# Buttons
new_class = new_class.replace('background: #1a3a4a;', 'background: $primary;')
new_class = new_class.replace('background: #1a0000;', 'background: $error-muted;')
new_class = new_class.replace('border: tall #330000;', 'border: tall $error;')
new_class = new_class.replace('background: #330000;', 'background: $error;')
new_class = new_class.replace('color: #ff4444;', 'color: $text;')
new_class = new_class.replace('background: #1a1500;', 'background: $warning-muted;')
new_class = new_class.replace('border: tall #332a00;', 'border: tall $warning;')
new_class = new_class.replace('background: #332a00;', 'background: $warning;')

# Clock alignment fix
new_class = new_class.replace('width: auto;', 'width: 100%;', 1) 
new_class = new_class.replace(
'''    #ascii_clock {
        text-align: center;
        color: $accent;
        text-style: bold;
        width: auto;
    }''',
'''    #ascii_clock {
        text-align: center;
        color: $accent;
        text-style: bold;
        width: 100%;
    }'''
)

# Build the final file
final_content = base_content + new_class + '\n'

with open('cli/tui/screens.py', 'w') as f:
    f.write(final_content)

print('SUCCESS: Replaced BunkerLauncherScreen with Gruvbox theme adjustments.')
