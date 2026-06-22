"""
Beginner-friendly Shell Commands Reference PDF
for the OnDevice HAR FQT+RigL Master Thesis project.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUT = "Shell_Commands_Reference_Beginner.pdf"

# ── Colour palette ──────────────────────────────────────────────────────────
C_LINUX    = colors.HexColor("#1a3a5c")   # dark navy  — Linux headings
C_PS       = colors.HexColor("#0063b1")   # MS blue    — PowerShell headings
C_CMD      = colors.HexColor("#2b2b2b")   # near-black — CMD headings
C_TIP      = colors.HexColor("#1e7e34")   # green      — tips
C_WARN     = colors.HexColor("#856404")   # amber      — warnings
C_LINUX_BG = colors.HexColor("#ddeeff")
C_PS_BG    = colors.HexColor("#e3f0ff")
C_CMD_BG   = colors.HexColor("#e8e8e8")
C_TIP_BG   = colors.HexColor("#d4edda")
C_WARN_BG  = colors.HexColor("#fff3cd")
C_TBLHDR   = colors.HexColor("#1a3a5c")
C_TBLALT   = colors.HexColor("#f0f5ff")
C_WHITE    = colors.white
C_GREY     = colors.HexColor("#555555")

W, H = A4
BODY_W = W - 4 * cm   # usable width

styles = getSampleStyleSheet()

# ── Style factories ─────────────────────────────────────────────────────────
def PS(name, parent="Normal", **kw):
    return ParagraphStyle(name + str(id(kw)), parent=styles[parent], **kw)

NORMAL  = PS("n",  fontSize=9.5,  leading=15,  textColor=colors.HexColor("#1a1a1a"), alignment=TA_JUSTIFY)
BODY    = PS("b",  fontSize=9.5,  leading=15,  textColor=colors.HexColor("#1a1a1a"), alignment=TA_JUSTIFY, spaceAfter=6)
SMALL   = PS("sm", fontSize=8.5,  leading=13,  textColor=C_GREY)
CODE    = PS("c",  fontName="Courier", fontSize=8.5, leading=13, textColor=colors.HexColor("#1a1a1a"))
CODE_SM = PS("cs", fontName="Courier", fontSize=7.5, leading=12, textColor=colors.HexColor("#1a1a1a"))
TH_STY  = PS("th", fontName="Helvetica-Bold", fontSize=8.5, textColor=C_WHITE)
TD_STY  = PS("td", fontName="Courier", fontSize=8, leading=12)
TD_N    = PS("tn", fontSize=8.5, leading=12)

def S(n=6):  story.append(Spacer(1, n))
def HR():    story.append(HRFlowable(width="100%", thickness=0.4, color=colors.lightgrey, spaceAfter=4))
def PB():    story.append(PageBreak())

# ── Heading helpers ─────────────────────────────────────────────────────────
def H1(text):
    story.append(Paragraph(text, PS("H1", fontSize=15, textColor=C_WHITE,
        backColor=C_LINUX, borderPadding=(7,10,7,10), spaceAfter=6, spaceBefore=16)))

def H2(text):
    story.append(Paragraph(text, PS("H2", fontSize=11, textColor=C_LINUX,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4, borderPadding=(0,0,2,0))))

def H3(text):
    story.append(Paragraph(text, PS("H3", fontSize=9.5, textColor=C_LINUX,
        fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2)))

def BD(text):
    story.append(Paragraph(text, BODY))

def NT(text):
    story.append(Paragraph(text, PS("nt", fontSize=8.5, leading=13,
        textColor=C_GREY, leftIndent=14, spaceAfter=3)))

# ── Tip / Warning boxes ─────────────────────────────────────────────────────
def tip_box(text, label="TIP", bg=C_TIP_BG, border=C_TIP):
    p = Paragraph(f"<b>{label}:</b>  {text}", PS("tip", fontSize=9, leading=13))
    t = Table([[p]], colWidths=[BODY_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), bg),
        ("BOX",(0,0),(-1,-1), 1, border),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(t); S(4)

def warn_box(text):
    tip_box(text, label="WARNING", bg=C_WARN_BG, border=colors.HexColor("#f0ad4e"))

# ── Code blocks ─────────────────────────────────────────────────────────────
def code_block(lines, bg=C_LINUX_BG, label=None):
    items = []
    if label:
        items.append(Paragraph(label, PS("cl", fontName="Helvetica-Bold",
            fontSize=8, textColor=C_WHITE, backColor=C_LINUX,
            borderPadding=(2,5,2,5))))
    items.append(Paragraph("<br/>".join(lines), CODE))
    t = Table([[item] for item in items], colWidths=[BODY_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), bg),
        ("BOX",(0,0),(-1,-1), 0.5, colors.grey),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(t); S(4)

def three_blocks(linux_lines, ps_lines, cmd_lines,
                 linux_note=None, ps_note=None, cmd_note=None):
    """Show the same operation in all three shells, side by side."""
    def cell(lines, bg, note):
        txt = "<br/>".join(lines)
        p = Paragraph(txt, CODE_SM)
        items = [p]
        if note:
            items.append(Paragraph(note, PS("nb", fontSize=7.5, textColor=C_GREY,
                leading=11, spaceAfter=2)))
        return items

    col = BODY_W / 3 - 2
    linux_cell = cell(linux_lines, C_LINUX_BG, linux_note)
    ps_cell    = cell(ps_lines,    C_PS_BG,    ps_note)
    cmd_cell   = cell(cmd_lines,   C_CMD_BG,   cmd_note)

    # Header row
    hdr = Table([
        [Paragraph("Linux / WSL", PS("lh", fontName="Helvetica-Bold", fontSize=8, textColor=C_WHITE)),
         Paragraph("PowerShell",  PS("ph", fontName="Helvetica-Bold", fontSize=8, textColor=C_WHITE)),
         Paragraph("Command Prompt", PS("ch", fontName="Helvetica-Bold", fontSize=8, textColor=C_WHITE))]
    ], colWidths=[col, col, col])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0), C_LINUX),
        ("BACKGROUND",(1,0),(1,0), C_PS),
        ("BACKGROUND",(2,0),(2,0), C_CMD),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("LEFTPADDING",(0,0),(-1,-1),6),
    ]))

    def mk_col(items, bg):
        rows = [[p] for p in items]
        t = Table(rows, colWidths=[col])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1), bg),
            ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("LEFTPADDING",(0,0),(-1,-1),6),
        ]))
        return t

    body = Table([[mk_col(linux_cell,C_LINUX_BG),
                   mk_col(ps_cell,C_PS_BG),
                   mk_col(cmd_cell,C_CMD_BG)]],
                 colWidths=[col, col, col])
    body.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,colors.grey),
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.grey),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))

    story.append(KeepTogether([hdr, body])); S(4)

# ── Comparison table ────────────────────────────────────────────────────────
def mk_table(rows, col_fracs, header_row=True):
    col_w = [BODY_W * f for f in col_fracs]
    data = []
    for i, r in enumerate(rows):
        if i == 0 and header_row:
            data.append([Paragraph(c, TH_STY) for c in r])
        else:
            data.append([Paragraph(c, TD_N) for c in r])
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), C_TBLHDR),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_WHITE, C_TBLALT]),
        ("BOX",(0,0),(-1,-1), 0.5, colors.grey),
        ("INNERGRID",(0,0),(-1,-1), 0.3, colors.lightgrey),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    story.append(t); S(6)

# ═══════════════════════════════════════════════════════════════════════════
# BUILD THE STORY
# ═══════════════════════════════════════════════════════════════════════════
story = []

# ── COVER ───────────────────────────────────────────────────────────────────
S(2*cm)
story.append(Paragraph(
    "Shell Commands Reference",
    PS("ttl","Title", fontSize=24, textColor=C_LINUX, alignment=TA_CENTER, spaceAfter=8)))
story.append(Paragraph(
    "A Complete Beginner's Guide",
    PS("sub","Normal", fontSize=13, textColor=C_PS, alignment=TA_CENTER, spaceAfter=4)))
story.append(Paragraph(
    "Linux / WSL  ·  PowerShell  ·  Command Prompt<br/>"
    "Tailored for the OnDevice HAR FQT+RigL Master Thesis Project",
    PS("sub2","Normal", fontSize=10, textColor=C_GREY, alignment=TA_CENTER, spaceAfter=20)))
HR()
S(6)
story.append(Paragraph(
    "This guide explains every terminal command you will use when building, "
    "training, and evaluating the FQT+RigL model on PC (Windows / WSL). "
    "Each command is explained from scratch — no prior Linux or terminal "
    "experience is assumed. Side-by-side comparisons show the same action "
    "in all three environments so you always know which version to type.",
    PS("intro","Normal", fontSize=9.5, leading=15, alignment=TA_JUSTIFY)))
S(8)

# Table of Contents
H2("Contents")
toc = [
    ("1", "What Is a Terminal (Shell)?", "2"),
    ("2", "The Three Shells: Linux/WSL, PowerShell, CMD", "2"),
    ("3", "How to Open Each Shell", "3"),
    ("4", "Reading the Prompt — How to Know Where You Are", "3"),
    ("5", "Understanding File Paths", "4"),
    ("6", "Navigation Commands — Moving Between Folders", "5"),
    ("7", "File and Folder Operations", "7"),
    ("8", "WSL — Running Linux Inside Windows", "9"),
    ("9", "Installing Software in WSL (apt)", "11"),
    ("10","CMake — Configuring and Building C Projects", "12"),
    ("11","Complete Project Workflow — Step by Step", "14"),
    ("12","Common Errors and How to Fix Them", "16"),
    ("13","Quick Reference Card", "18"),
]
toc_data = [["#", "Section", "Page"]] + [[n,t,p] for n,t,p in toc]
mk_table(toc_data, [0.06, 0.79, 0.15])

PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("1.  What Is a Terminal (Shell)?")
S(4)
BD("When you use a computer normally, you click icons and menus — that is "
   "called a <b>Graphical User Interface (GUI)</b>. A <b>terminal</b> (also "
   "called a <b>shell</b> or <b>command line</b>) is a text-only window where "
   "you type commands to make the computer do things.")
BD("Think of it like giving spoken instructions to a very precise assistant. "
   "Instead of clicking File → Open, you type the instruction. The advantage "
   "is speed: tasks that take many clicks become one short command. "
   "For software development — especially building C projects — the terminal "
   "is essential because compilation tools like <b>cmake</b> and <b>gcc</b> "
   "have no GUI.")
tip_box("You do not need to memorise everything at once. Bookmark this PDF "
        "and look up commands as you need them.")

H2("Basic rules that apply to ALL shells")
mk_table([
    ["Rule", "Explanation"],
    ["Press Enter to run a command",
     "Type your command, then press Enter. Nothing happens until you press Enter."],
    ["Commands are case-sensitive in Linux",
     "ls and LS are different in Linux/WSL. PowerShell and CMD are not case-sensitive."],
    ["Spaces matter in paths",
     'If a folder name has spaces, wrap the whole path in quotes: cd "My Folder"'],
    ["Press Ctrl+C to stop",
     "If a program is running and you want to stop it, press Ctrl+C."],
    ["Up arrow = previous command",
     "Press the Up arrow key to recall the last command you ran. "
     "Press it again for the one before that."],
    ["Tab = autocomplete",
     "Type the first few letters of a file/folder name and press Tab. "
     "The shell will complete it for you."],
    ["# starts a comment",
     "Any line starting with # is ignored. Comments are notes for humans."],
], [0.30, 0.70])

PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("2.  The Three Shells: Linux/WSL, PowerShell, and CMD")
S(4)
BD("Windows gives you multiple shell environments. This project uses three. "
   "Understanding which one you are in — and which to use — prevents most "
   "beginner errors.")
S(4)
mk_table([
    ["Shell", "Full Name", "Background Colour", "When to Use It"],
    ["Linux / WSL\n(bash)",
     "Windows Subsystem\nfor Linux — Bash shell",
     "Usually dark/black\nwith coloured prompt",
     "Building the C project with cmake and gcc. "
     "Installing Linux packages. "
     "Running Python scripts. "
     "ALL compilation work goes here."],
    ["PowerShell",
     "Windows PowerShell\nor PowerShell 7",
     "Blue background\n(classic) or dark",
     "Managing files and folders on Windows. "
     "Renaming CMakeLists files. "
     "General Windows automation."],
    ["Command Prompt\n(CMD)",
     "cmd.exe — the\nclassic Windows shell",
     "Black background\nno colour",
     "Simple Windows commands. "
     "Shutting down WSL (wsl --shutdown). "
     "Legacy batch scripts."],
], [0.15, 0.20, 0.18, 0.47])
S(4)
tip_box("For this project, you will spend most of your time in "
        "<b>Linux / WSL</b>. Use PowerShell only for Windows file management "
        "tasks (renaming files, etc.).")
warn_box("Commands are NOT interchangeable between shells. "
         "A Linux command like rm will not work in CMD. "
         "A PowerShell command like Remove-Item will not work in Linux. "
         "Always check which shell you are in before typing.")

PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("3.  How to Open Each Shell")
S(4)
H2("Opening Linux / WSL")
BD("WSL must be installed first (it comes pre-installed on Windows 11, "
   "and can be installed on Windows 10 via the Microsoft Store).")
code_block([
    "Method 1: Press the Windows key, type 'wsl', press Enter.",
    "Method 2: Open PowerShell or CMD and type:   wsl",
    "Method 3: Right-click the Start button → 'Terminal' → open a new",
    "          tab and choose Ubuntu.",
], C_LINUX_BG, label="How to open WSL")
H2("Opening PowerShell")
code_block([
    "Method 1: Press Windows key, type 'PowerShell', press Enter.",
    "Method 2: Press Win+X (right-click Start button) → 'Windows PowerShell'",
    "          or 'Windows Terminal'.",
    "Method 3: Inside any open terminal window, click the + button",
    "          (new tab) and select PowerShell.",
], C_PS_BG, label="How to open PowerShell")
H2("Opening Command Prompt (CMD)")
code_block([
    "Method 1: Press Windows key, type 'cmd', press Enter.",
    "Method 2: Press Win+R, type 'cmd', press Enter.",
    "Method 3: In the search bar type 'Command Prompt'.",
], C_CMD_BG, label="How to open Command Prompt")
tip_box("Windows Terminal (available from the Microsoft Store) is the "
        "modern replacement that lets you have Linux, PowerShell, and CMD "
        "all as tabs in one window. Highly recommended.")

PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("4.  Reading the Prompt — How to Know Where You Are")
S(4)
BD("The <b>prompt</b> is the text that appears before the flashing cursor. "
   "It tells you which shell you are in and where on the filesystem you currently are. "
   "Reading the prompt correctly prevents you from running commands in the wrong place.")
S(4)
code_block([
    "matef@LAPTOP:~$                  <-- Linux / WSL",
    "   |      |   |",
    "   |      |   +-- $ means normal user (# means administrator/root)",
    "   |      +------ name of the computer",
    "   +------------- your Linux username",
    "",
    "matef@LAPTOP:~/har_build$        <-- WSL, currently inside ~/har_build",
    "matef@LAPTOP:/mnt/f/project$     <-- WSL, on Windows drive F:",
], C_LINUX_BG, label="Linux / WSL prompt — examples")
S(2)
code_block([
    "PS C:\\Users\\matef>               <-- PowerShell",
    "   |  |",
    "   |  +-- current folder on Windows (C:\\Users\\matef)",
    "   +----- 'PS' always appears at the start in PowerShell",
    "",
    "PS C:\\Users\\matef\\har_project>   <-- inside a subfolder",
], C_PS_BG, label="PowerShell prompt — examples")
S(2)
code_block([
    "C:\\Users\\matef>                  <-- Command Prompt",
    "   |",
    "   +-- current folder (no prefix, just the path and >)",
    "",
    "F:\\technical material>           <-- CMD on drive F:",
], C_CMD_BG, label="Command Prompt prompt — examples")
tip_box("If you are ever unsure which shell you are in, look at the very "
        "beginning of the line. PS = PowerShell, username@computer = WSL/Linux, "
        "just a path = CMD.")

PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("5.  Understanding File Paths")
S(4)
BD("A <b>path</b> is the address of a file or folder on the computer. "
   "Think of it like a postal address — it tells the computer exactly where "
   "something is located. Linux and Windows use different formats.")

H2("5.1  Windows paths (PowerShell and CMD)")
BD("Windows uses a <b>drive letter</b> (like C: or F:) followed by "
   "backslashes (\\) between folder names.")
code_block([
    "F:\\technical material\\Master thesis\\claude\\on_device training",
    "^                     ^                         ^",
    "|                     |                         +-- innermost folder",
    "|                     +-- subfolder",
    "+-- drive letter (F:)",
], C_CMD_BG, label="Windows path format")
H2("5.2  Linux paths (WSL / bash)")
BD("Linux has no drive letters. Everything starts from / (called 'root'). "
   "Linux uses forward slashes (/) between folder names.")
code_block([
    "/home/matef/har_build",
    "^    ^      ^",
    "|    |      +-- your project folder",
    "|    +-- your Linux home folder",
    "+-- root of the entire filesystem",
    "",
    "~   means 'my home folder' — a shortcut for /home/matef",
], C_LINUX_BG, label="Linux path format")
H2("5.3  How WSL sees Windows drives")
BD("WSL mounts Windows drives under <b>/mnt/</b>. "
   "Drive F:\\ becomes /mnt/f/, drive C:\\ becomes /mnt/c/.")
code_block([
    "Windows path:  F:\\technical material\\Master thesis\\...",
    "WSL path:      /mnt/f/technical material/Master thesis/...",
    "",
    "Windows path:  C:\\Users\\matef\\Documents",
    "WSL path:      /mnt/c/Users/matef/Documents",
    "",
    "Rule: replace  F:\\  with  /mnt/f/",
    "      replace  \\   with  /",
], C_LINUX_BG, label="Windows ↔ WSL path translation")

H2("5.4  Absolute vs. relative paths")
mk_table([
    ["Type", "Starts With", "Meaning", "Example"],
    ["Absolute path",
     "/ or C:\\ or F:\\",
     "Full address from the very top of the filesystem. "
     "Always works no matter where you currently are.",
     "/mnt/f/project/src/main.c"],
    ["Relative path",
     "A folder name or . or ..",
     "Address relative to where you currently are. "
     ". means 'here'. .. means 'go up one level'.",
     "src/main.c  (if you are already in /mnt/f/project)"],
], [0.18, 0.16, 0.38, 0.28])
tip_box("When in doubt, use absolute paths — they are unambiguous. "
        "Relative paths are shorter but only work if you are in the right folder.")
PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("6.  Navigation Commands — Moving Between Folders")
S(4)
BD("The most common task in a terminal is navigating between folders "
   "(also called directories). These four commands cover 90% of navigation.")

H2("6.1  pwd — Print Working Directory (where am I?)")
BD("<b>pwd</b> stands for 'print working directory'. It prints the full "
   "path of the folder you are currently in. Use it whenever you are "
   "unsure where you are.")
three_blocks(
    ["$ pwd", "/home/matef/har_build"],
    ["PS> pwd", "Path", "----", "C:\\Users\\matef"],
    ["C:\\> cd", "C:\\Users\\matef"],
    linux_note="In WSL: pwd shows the Linux path",
    ps_note="PowerShell: pwd or Get-Location",
    cmd_note="CMD: typing cd with no argument shows current folder",
)

H2("6.2  cd — Change Directory (move to a different folder)")
BD("<b>cd</b> stands for 'change directory'. It moves you to a different "
   "folder. Think of it as double-clicking a folder icon, but in text form.")
code_block([
    "Syntax:  cd <path-to-folder>",
    "",
    "# Go into a subfolder called 'src' (relative path)",
    "cd src",
    "",
    "# Go into an absolute path",
    'cd "/mnt/f/technical material/Master thesis/claude/on_device training"',
    "",
    "# Go up one level (to the parent folder)",
    "cd ..",
    "",
    "# Go to your home folder",
    "cd ~",
    "",
    "# Go to the root of the filesystem",
    "cd /",
], C_LINUX_BG, label="cd examples (Linux / WSL)")
S(2)
code_block([
    "# Important: wrap paths with spaces in DOUBLE QUOTES",
    'cd "F:\\technical material\\Master thesis"',
    "",
    "# Go up one level",
    "cd ..",
    "",
    "# Go to your user home",
    "cd $HOME      # PowerShell",
    "cd %USERPROFILE%   # CMD",
], C_PS_BG, label="cd examples (PowerShell / CMD)")
warn_box("In Linux, folder names are case-sensitive. "
         "'cd Documents' and 'cd documents' go to different places "
         "(or one may not exist). In Windows, case does not matter.")

H2("6.3  ls — List files and folders")
BD("<b>ls</b> (Linux) or <b>dir</b> (Windows CMD) shows everything inside "
   "the current folder. Use it to see what is here before navigating further.")
three_blocks(
    ["$ ls         # simple list",
     "$ ls -la     # detailed list",
     "             # (shows hidden files,",
     "             # sizes, permissions)"],
    ["PS> ls       # works in PowerShell too",
     "PS> dir      # alias — same result",
     "PS> ls -la   # NOT valid in PS",
     "PS> Get-ChildItem  # full command"],
    ["C:\\> dir     # shows all files",
     "C:\\> dir /a  # include hidden",
     "",
     ""],
    linux_note="-l = long format, -a = all (including hidden files starting with .)",
    ps_note="PowerShell's ls is an alias for Get-ChildItem",
    cmd_note="dir is the only option in CMD",
)
tip_box("Run ls (or dir) whenever you are not sure what is in the current "
        "folder. It is the equivalent of opening a folder window in Explorer.")

H2("6.4  Navigating to the project folder — full example")
BD("This is the exact sequence to get from anywhere to the project folder "
   "inside WSL, then build it:")
code_block([
    "# Step 1: Open WSL (type 'wsl' in PowerShell or search 'WSL')",
    "# You will see the prompt: matef@LAPTOP:~$",
    "",
    "# Step 2: Navigate to the project",
    'cd "/mnt/f/technical material/Master thesis/claude/on_device training"',
    "",
    "# Step 3: Confirm you are in the right place",
    "pwd",
    "# Expected output:",
    "# /mnt/f/technical material/Master thesis/claude/on_device training",
    "",
    "# Step 4: List what is here",
    "ls",
    "# You should see: OnDeviceTraining  OnDeviceTraining_HAR_FQT_RigL  ...",
], C_LINUX_BG, label="Complete navigation example")
PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("7.  File and Folder Operations")
S(4)
BD("These commands let you create, delete, rename, copy, and inspect files "
   "and folders without using the mouse. They work across all three shells, "
   "but the command names differ.")

H2("7.1  mkdir — Make a new folder")
BD("<b>mkdir</b> creates a new empty folder. It stands for 'make directory'.")
three_blocks(
    ["$ mkdir build",
     "$ mkdir -p a/b/c",
     "# -p creates parent folders",
     "# that don't exist yet"],
    ["PS> mkdir build",
     "PS> mkdir -Force a\\b\\c",
     "# -Force creates parents",
     ""],
    ["C:\\> mkdir build",
     "C:\\> md build",
     "# md is an alias",
     ""],
    linux_note="-p prevents error if folder already exists",
    ps_note="Both mkdir and md work in PowerShell",
    cmd_note="md is shorthand for mkdir in CMD",
)

H2("7.2  rm / del — Delete files or folders")
BD("Deleting from the terminal is <b>permanent</b> — files do NOT go to "
   "the Recycle Bin. Double-check before running these commands.")
warn_box("There is NO undo in the terminal. Once you delete with rm -rf "
         "or rmdir /s /q, the files are gone. Be very careful with these commands.")
three_blocks(
    ["$ rm file.txt",
     "# delete one file",
     "",
     "$ rm -rf foldername",
     "# delete a folder and",
     "# EVERYTHING inside it",
     "# -r = recursive (subfolders)",
     "# -f = force (no confirmation)"],
    ["PS> Remove-Item file.txt",
     "# delete one file",
     "",
     "PS> Remove-Item -Recurse -Force foldername",
     "# delete folder + contents",
     "# -Recurse = include subfolders",
     "# -Force = no confirmation"],
    ["C:\\> del file.txt",
     "# delete one file",
     "",
     "C:\\> rmdir /s /q foldername",
     "# delete folder + contents",
     "# /s = include subfolders",
     "# /q = quiet (no confirmation)"],
)

H2("7.3  mv / Rename-Item — Rename or move a file")
BD("In Linux, <b>mv</b> (move) handles both renaming and moving. "
   "In Windows, renaming uses <b>Rename-Item</b> (PowerShell) or <b>ren</b> (CMD).")
three_blocks(
    ["$ mv old.txt new.txt",
     "# rename old.txt to new.txt",
     "",
     "$ mv file.txt /mnt/f/other/",
     "# move file to a different folder"],
    ["PS> Rename-Item old.txt new.txt",
     "# rename a file",
     "",
     "PS> Move-Item file.txt C:\\other\\",
     "# move a file"],
    ["C:\\> ren old.txt new.txt",
     "# rename a file",
     "",
     "C:\\> move file.txt C:\\other\\",
     "# move a file"],
)
BD("Renaming the CMake files (which you had to do in this project) looks like this:")
code_block([
    "# In PowerShell — rename the Pico cmake file first, then rename the PC file:",
    "",
    "PS C:\\...\\OnDeviceTraining_HAR_FQT_RigL> Rename-Item CMakeLists.txt CMakeLists_Pico.txt",
    "PS C:\\...\\OnDeviceTraining_HAR_FQT_RigL> Rename-Item CMakeLists_PC.txt CMakeLists.txt",
    "",
    "# Why rename in this order?",
    "# If CMakeLists.txt already exists, you cannot rename CMakeLists_PC.txt",
    "# to that name until the existing one has been moved out of the way first.",
], C_PS_BG, label="Renaming CMakeLists files — project-specific example")

H2("7.4  cp / Copy-Item — Copy a file")
three_blocks(
    ["$ cp source.txt dest.txt",
     "# copy one file",
     "$ cp -r folder/ dest/",
     "# copy entire folder (-r)"],
    ["PS> Copy-Item source.txt dest.txt",
     "",
     "PS> Copy-Item -Recurse folder dest",
     ""],
    ["C:\\> copy source.txt dest.txt",
     "",
     "C:\\> xcopy folder dest /E /I",
     "# /E includes subfolders"],
)

H2("7.5  cat / type — View file contents without opening an editor")
three_blocks(
    ["$ cat filename.txt",
     "# print file to screen",
     "$ head -20 filename.txt",
     "# show first 20 lines only"],
    ["PS> Get-Content filename.txt",
     "# print file to screen",
     "PS> Get-Content file.txt | Select -First 20",
     "# first 20 lines"],
    ["C:\\> type filename.txt",
     "# print file to screen",
     "",
     ""],
)

H2("7.6  Chaining commands — running multiple commands in sequence")
BD("You often want to run several commands in a row. The way to chain them "
   "differs between shells — this is a common source of errors.")
mk_table([
    ["Symbol", "Shell", "Meaning", "Example"],
    ["&&", "Linux / CMD", "Run the second command ONLY if the first succeeded "
     "(exit code 0 = success).", "mkdir build && cd build"],
    [";", "Linux / PowerShell", "Run both commands regardless of whether the "
     "first succeeded or failed.", "mkdir build ; cd build"],
    ["&", "CMD only", "Run both commands regardless of result (CMD version of ;).",
     "mkdir build & cd build"],
    ["|", "All shells", "Pipe — send the OUTPUT of the first command as "
     "INPUT to the second. Used for filtering.", "ls | grep main"],
], [0.10, 0.18, 0.45, 0.27])
warn_box("&& does NOT work in PowerShell. PowerShell treats && as a "
         "bitwise AND operator and shows a syntax error. Use ; or separate lines instead.")
code_block([
    "# WRONG in PowerShell — causes error:",
    "mkdir build_pc && cd build_pc",
    "",
    "# CORRECT in PowerShell (two options):",
    "mkdir build_pc",
    "cd build_pc",
    "# OR on one line:",
    "mkdir build_pc ; cd build_pc",
], C_WARN_BG, label="The && vs ; mistake — very common for beginners")
PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("8.  WSL — Running Linux Inside Windows")
S(4)
BD("<b>WSL</b> (Windows Subsystem for Linux) is a feature of Windows 10/11 "
   "that runs a real Linux environment (Ubuntu) directly inside Windows, "
   "without needing a separate computer or virtual machine.")
BD("For this project, WSL is essential because the compiler (GCC 10+) and "
   "build tools required by the OnDeviceTraining framework are only available "
   "in Linux. The MinGW GCC bundled with CodeBlocks on Windows is version 8.1 "
   "— too old for the framework's C11 patterns.")

H2("8.1  WSL control commands — typed in PowerShell or CMD")
mk_table([
    ["Command", "Where to Type It", "What It Does"],
    ["wsl", "PowerShell or CMD",
     "Open a WSL bash terminal. You will see the Linux prompt."],
    ["wsl --list", "PowerShell or CMD",
     "Show all installed Linux distributions (e.g. Ubuntu-22.04)."],
    ["wsl --version", "PowerShell or CMD",
     "Show the WSL and kernel version numbers."],
    ["wsl --shutdown", "PowerShell or CMD",
     "Stop ALL running WSL instances immediately. "
     "This releases any file locks WSL has on Windows folders, "
     "which is necessary when Windows cannot delete a folder that WSL has open."],
    ["exit", "Inside WSL",
     "Leave the WSL terminal and return to PowerShell or CMD."],
], [0.25, 0.20, 0.55])

H2("8.2  How WSL and Windows share files")
BD("WSL and Windows run side by side and can see each other's files, "
   "but they use different path formats to refer to the same locations.")
code_block([
    "From Windows (PowerShell/CMD)           From WSL (bash)",
    "─────────────────────────────────────   ──────────────────────────────────────",
    "F:\\technical material\\project           /mnt/f/technical material/project",
    "C:\\Users\\matef\\Documents                /mnt/c/Users/matef/Documents",
    "C:\\Users\\matef                          /mnt/c/Users/matef   OR   ~",
    "",
    "Translation rule:",
    "  Drive letter + colon  →  /mnt/ + lowercase drive letter",
    "  Backslash \\           →  Forward slash /",
], C_LINUX_BG, label="Windows ↔ WSL path translation table")

H2("8.3  Why we build in the WSL native home folder")
BD("You might expect to build the project directly in the Windows folder "
   "(F:\\...) from inside WSL. This usually works, but some file operations "
   "(creating and deleting folders, permissions) behave unexpectedly on "
   "Windows-mounted drives accessed from Linux. This is called a "
   "<b>DrvFS limitation</b>.")
BD("The solution is to build in the Linux native home folder "
   "(<font face='Courier'>~/har_build</font>), which has no such restrictions. "
   "The source code stays in F:\\, but the compiled output goes into ~/har_build.")
code_block([
    "Source code (stays in Windows):   /mnt/f/.../OnDeviceTraining_HAR_FQT_RigL/",
    "Build output (goes into Linux):   ~/har_build/",
    "                                  (which is /home/matef/har_build/)",
    "",
    "cmake is told where the source is:",
    '  cmake "/mnt/f/.../OnDeviceTraining_HAR_FQT_RigL"',
    "",
    "cmake reads CMakeLists.txt from that path and writes build files",
    "to the CURRENT FOLDER (~/har_build).",
], C_LINUX_BG, label="Source vs. build directory — the split")
tip_box("~/har_build is persistent — it survives closing and reopening WSL. "
        "You only need to run cmake once (to configure). "
        "After that, just run cmake --build . to recompile after code changes.")

H2("8.4  When WSL locks a Windows folder — and how to fix it")
BD("WSL sometimes holds a file lock on a Windows folder, preventing you from "
   "deleting it from Windows Explorer or PowerShell. The fix is always the same:")
code_block([
    "Step 1: In PowerShell or CMD, shut down WSL:",
    "        wsl --shutdown",
    "",
    "Step 2: Wait 5 seconds, then delete the folder from Windows:",
    "        Remove-Item -Recurse -Force build_pc",
    "        # or in CMD:",
    "        rmdir /s /q build_pc",
    "",
    "Step 3: Reopen WSL:",
    "        wsl",
], C_WARN_BG, label="Fixing 'The process cannot access the file' error")
PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("9.  Installing Software in WSL (apt)")
S(4)
BD("WSL runs Ubuntu Linux. Ubuntu uses a package manager called <b>apt</b> "
   "(Advanced Package Tool) to install software. Think of it like the App Store, "
   "but operated entirely from the terminal.")
BD("<b>sudo</b> means 'superuser do' — it temporarily grants you administrator "
   "privileges for one command. Linux requires this for installing software. "
   "WSL will ask for your Linux password the first time.")

H2("9.1  Installing all required tools for this project")
BD("Run these commands <b>one at a time</b>. Wait for each one to finish "
   "before typing the next.")
code_block([
    "# Command 1: Update the list of available packages",
    "# (This does NOT install anything — it just refreshes the catalogue)",
    "sudo apt update",
    "",
    "# What you will see:",
    "# [sudo] password for matef:    <- type your Linux password, press Enter",
    "# Hit:1 http://archive.ubuntu.com ...  <- downloading package lists",
    "# Reading package lists... Done",
    "",
    "# Command 2: Install cmake, gcc, g++, and make",
    "# -y means 'yes to all questions' (so it doesn't ask you to confirm each package)",
    "sudo apt install -y cmake gcc g++ make",
    "",
    "# What you will see:",
    "# Reading package lists... Done",
    "# Building dependency tree... Done",
    "# The following NEW packages will be installed: ...",
    "# Do you want to continue? [Y/n]   <- press Enter (or -y skips this)",
    "# ... lots of download/install output ...",
    "# Processing triggers for ... Done",
    "",
    "# Command 3: Verify everything installed correctly",
    "cmake --version      # should print: cmake version 3.x.x",
    "gcc --version        # should print: gcc (Ubuntu ...) 12.x.x",
    "make --version       # should print: GNU Make 4.x",
], C_LINUX_BG, label="Full installation sequence")

H2("9.2  Common apt commands reference")
mk_table([
    ["Command", "What It Does"],
    ["sudo apt update", "Refresh the package list (run this first, always)"],
    ["sudo apt install -y package", "Install a package. -y skips confirmation."],
    ["sudo apt remove package", "Uninstall a package."],
    ["sudo apt upgrade", "Update all installed packages to their latest versions."],
    ["apt search keyword", "Search for a package by name or keyword."],
    ["dpkg -l | grep name", "Check if a package is already installed."],
], [0.35, 0.65])
tip_box("If apt install fails with 'package not found', run sudo apt update first "
        "and try again. The package list may be outdated.")
warn_box("Do NOT install multiple packages across separate commands in a rapid "
         "sequence without waiting. Paste one command, wait for the Done message, "
         "then paste the next.")
PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("10.  CMake — Configuring and Building C Projects")
S(4)
BD("<b>CMake</b> is a build system generator. It reads a file called "
   "<b>CMakeLists.txt</b> and produces the actual build instructions that "
   "make/ninja then use to compile your C code.")
BD("Building a project always happens in <b>two separate steps</b>: "
   "<b>configure</b> (cmake reads CMakeLists.txt and prepares everything), "
   "then <b>build</b> (cmake --build . actually compiles the code).")

H2("10.1  The CMake two-step workflow")
code_block([
    "STEP 1: Create a separate build folder and go into it",
    "        (NEVER run cmake inside your source code folder)",
    "mkdir -p ~/har_build",
    "cd ~/har_build",
    "",
    "STEP 2: Configure — tell cmake where the source code is",
    '        cmake "/mnt/f/technical material/Master thesis/claude/on_device training/OnDeviceTraining_HAR_FQT_RigL"',
    "",
    "        cmake reads CMakeLists.txt from that source folder",
    "        and writes build files into ~/har_build (your current folder).",
    "",
    "        Successful output ends with:",
    "        -- Build files have been written to: /home/matef/har_build",
    "",
    "STEP 3: Build — compile the code",
    "cmake --build .",
    "",
    "        . means 'this folder' (~/har_build, where cmake wrote the build files)",
    "        Successful output ends with:",
    "        [100%] Built target har_fqt_rigl",
], C_LINUX_BG, label="The three-step cmake workflow")

H2("10.2  What each cmake output percentage means")
mk_table([
    ["Output line", "What is happening"],
    ["-- Found Python...", "CMake is checking what tools are available on your system"],
    ["-- Configuring done", "cmake has read all CMakeLists.txt files successfully"],
    ["-- Build files have been written to: ...", "Configure is finished; you can now run cmake --build"],
    ["[ 10%] Compiling C object ...", "GCC is compiling one .c source file"],
    ["[ 80%] Linking C executable ...", "All .o object files are being linked into the final program"],
    ["[100%] Built target har_fqt_rigl", "Compilation succeeded. The executable is ready."],
], [0.38, 0.62])

H2("10.3  Important: CMakeLists.txt must be named exactly that")
BD("CMake always looks for a file called exactly "
   "<font face='Courier'>CMakeLists.txt</font> (capital C, capital L, .txt extension). "
   "There is <b>no</b> <font face='Courier'>-f</font> flag to specify a "
   "different filename.")
code_block([
    "# WRONG — this flag does not exist:",
    "cmake -f CMakeLists_PC.txt ..     # ERROR: Unknown argument '-f'",
    "",
    "# CORRECT — rename the file first, then run cmake:",
    "# (In PowerShell)",
    "Rename-Item CMakeLists.txt     CMakeLists_Pico.txt",
    "Rename-Item CMakeLists_PC.txt  CMakeLists.txt",
    "# Now cmake will find it automatically",
], C_WARN_BG, label="The -f flag mistake — does not exist in cmake")

H2("10.4  Re-building after code changes")
BD("After you edit a .c or .h file, you do NOT need to re-run cmake (configure). "
   "Just re-run the build step:")
code_block([
    "# Go to the build folder",
    "cd ~/har_build",
    "",
    "# Recompile only the changed files (cmake is smart about this)",
    "cmake --build .",
    "",
    "# To do a completely clean rebuild (delete everything and start over):",
    "cd ~",
    "rm -rf har_build",
    "mkdir har_build",
    "cd har_build",
    'cmake "/mnt/f/.../OnDeviceTraining_HAR_FQT_RigL"',
    "cmake --build .",
], C_LINUX_BG, label="Incremental vs. clean rebuild")
PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("11.  Complete Project Workflow — Step by Step")
S(4)
BD("Follow these steps in exact order from a fresh WSL terminal. "
   "Each step must finish without errors before you move to the next. "
   "Do NOT paste multiple commands at once.")

H2("Phase 1 — First-time setup (do only once)")
code_block([
    "# Open WSL (search 'wsl' in Windows Start menu)",
    "# You will see:  matef@LAPTOP:~$",
    "",
    "# 1a. Update package list",
    "sudo apt update",
    "# Wait for: 'Reading package lists... Done'",
    "",
    "# 1b. Install build tools",
    "sudo apt install -y cmake gcc g++ make",
    "# Wait for: 'done' on the last line",
    "",
    "# 1c. Verify",
    "cmake --version",
    "gcc --version",
    "# Both should print version numbers without error",
], C_LINUX_BG, label="Phase 1: Install tools")
S(4)

H2("Phase 2 — Create the build folder (do once per clean build)")
code_block([
    "# 2a. Create a build folder in the Linux home directory",
    "mkdir -p ~/har_build",
    "",
    "# 2b. Go into it",
    "cd ~/har_build",
    "",
    "# 2c. Confirm you are in the right place",
    "pwd",
    "# Expected: /home/matef/har_build",
    "",
    "# 2d. Configure the project (point cmake at the source code)",
    'cmake "/mnt/f/technical material/Master thesis/claude/on_device training/OnDeviceTraining_HAR_FQT_RigL"',
    "",
    "# Expected final line:",
    "# -- Build files have been written to: /home/matef/har_build",
], C_LINUX_BG, label="Phase 2: Configure")
S(4)

H2("Phase 3 — Compile the project")
code_block([
    "# Still inside ~/har_build",
    "cmake --build .",
    "",
    "# You will see lines like:",
    "# [  2%] Building C object ...",
    "# [ 12%] Building C object ...",
    "# ...",
    "# [100%] Built target har_fqt_rigl",
    "",
    "# If you see errors, check Section 12 (Common Errors).",
    "# If it says [100%] Built target har_fqt_rigl — you are done!",
    "",
    "# Find the compiled executable:",
    "ls ~/har_build/",
    "# You should see: har_fqt_rigl  (among other files)",
], C_LINUX_BG, label="Phase 3: Compile")
S(4)

H2("Phase 4 — Prepare the dataset (do once)")
code_block([
    "# Navigate to the OnDeviceTraining root folder",
    'cd "/mnt/f/technical material/Master thesis/claude/on_device training/OnDeviceTraining"',
    "",
    "# Run the data preparation script",
    "python3 examples/har_classifier/prepare_data.py",
    "",
    "# This script downloads and converts the UCI-HAR dataset into .npy files:",
    "#   train_x.npy, train_y.npy",
    "#   val_x.npy,   val_y.npy",
    "#   test_x.npy,  test_y.npy",
    "",
    "# Verify the files were created:",
    "ls examples/har_classifier/data/",
], C_LINUX_BG, label="Phase 4: Prepare dataset")
S(4)

H2("Phase 5 — Run the training")
code_block([
    "# Run from the OnDeviceTraining root so the data paths resolve correctly",
    'cd "/mnt/f/technical material/Master thesis/claude/on_device training/OnDeviceTraining"',
    "",
    "# Start training",
    "~/har_build/har_fqt_rigl",
    "",
    "# The program will print:",
    "#  === Model Summary ===",
    "#  Epoch 1/20 ...",
    "#  Training Loss: 1.xxxx  Train Acc: xx.x%",
    "#  ...",
    "#  === Sparsity Table (RigL) ===",
    "#  === FLOPs Report ===",
    "#  === Classification Report ===",
    "#  Confusion Matrix:",
    "",
    "# To stop training at any time: press Ctrl+C",
], C_LINUX_BG, label="Phase 5: Train the model")
PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("12.  Common Errors and How to Fix Them")
S(4)
BD("These are the errors most commonly encountered during this project. "
   "Each entry explains WHAT the error means, WHY it happens, and exactly "
   "HOW to fix it.")

errors = [
    (
        "'&&' is not a valid statement separator in this version.",
        "You typed && in PowerShell, which does not support it as a command separator.",
        "Replace && with ; or put each command on its own line:\n"
        "mkdir build_pc\ncd build_pc",
        C_PS_BG, C_PS
    ),
    (
        "cmake: command not found",
        "CMake has not been installed in WSL yet.",
        "Run: sudo apt update\nThen: sudo apt install -y cmake gcc g++ make",
        C_LINUX_BG, C_LINUX
    ),
    (
        "CMake Error: Unknown argument -f\n(or: cmake: invalid option -- 'f')",
        "You tried to use cmake -f to specify a custom filename.\n"
        "CMake does not have a -f flag. It always reads CMakeLists.txt.",
        "Rename your file first:\nRename-Item CMakeLists_PC.txt CMakeLists.txt\n"
        "Then run cmake without -f.",
        C_WARN_BG, colors.HexColor("#f0ad4e")
    ),
    (
        "CMake Error: The source directory does not appear to contain CMakeLists.txt.",
        "cmake cannot find the source code. The path you gave is wrong, "
        "or CMakeLists.txt has not been renamed yet.",
        "Check the path is correct (ls it first).\n"
        "Make sure CMakeLists.txt exists (not CMakeLists_PC.txt).",
        C_WARN_BG, colors.HexColor("#f0ad4e")
    ),
    (
        "CMake Error: The current CMakeCache.txt directory is not the same as\n"
        "the directory CMakeCache.txt was written to.  (or: not a CMake build directory)",
        "You ran cmake --build . from the wrong folder. You must be inside "
        "the build folder (~/har_build), not the source folder.",
        "cd ~/har_build\nthen try cmake --build . again.",
        C_WARN_BG, colors.HexColor("#f0ad4e")
    ),
    (
        "error: a label can only be part of a statement and a declaration\nis not a statement",
        "You are using MinGW GCC 8.1 (the Windows GCC bundled with CodeBlocks). "
        "It is too old. The OnDeviceTraining framework requires GCC 10 or newer.",
        "Switch to WSL. WSL comes with Ubuntu's GCC 12, which handles this correctly.",
        C_WARN_BG, colors.HexColor("#f0ad4e")
    ),
    (
        "rm: cannot remove 'build_pc': Permission denied\n"
        "(or: The process cannot access the file because it is\nbeing used by another process)",
        "WSL has the folder locked open (open file handle). Windows cannot "
        "delete a folder that Linux has open.",
        "In PowerShell/CMD:\nwsl --shutdown\n"
        "(wait 5 seconds)\nRemove-Item -Recurse -Force build_pc\nwsl",
        C_WARN_BG, colors.HexColor("#f0ad4e")
    ),
    (
        "mkdir: cannot create directory 'build_pc': File exists",
        "The folder already exists. mkdir fails if the destination already exists.",
        "In Linux: use mkdir -p (the -p flag suppresses this error):\n"
        "mkdir -p build_pc\n"
        "Or delete the existing folder first, then recreate it.",
        C_LINUX_BG, C_LINUX
    ),
    (
        "Cannot open file 'train_x.npy' (or similar .npy file)",
        "The dataset has not been prepared yet, or the program is being run "
        "from the wrong working directory.",
        "Run prepare_data.py first:\n"
        "python3 examples/har_classifier/prepare_data.py\n"
        "Then run the executable FROM the OnDeviceTraining root folder.",
        C_LINUX_BG, C_LINUX
    ),
]

for err_txt, cause_txt, fix_txt, bg, border in errors:
    err_lines  = err_txt.replace("\n", "<br/>")
    cause_lines= cause_txt.replace("\n", "<br/>")
    fix_lines  = fix_txt.replace("\n", "<br/>")

    p_err   = Paragraph(f'<b>Error:</b> <font face="Courier" size="8">{err_lines}</font>',
                        PS("e", fontSize=8.5, leading=13))
    p_cause = Paragraph(f"<b>Cause:</b> {cause_lines}", PS("ca",fontSize=8.5,leading=13))
    p_fix   = Paragraph(f"<b>Fix:</b> <font face='Courier' size='8'>{fix_lines}</font>",
                        PS("fx",fontSize=8.5,leading=13))
    rows = [[p_err], [p_cause], [p_fix]]
    t = Table(rows, colWidths=[BODY_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), bg),
        ("BOX",(0,0),(-1,-1),1,border),
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.lightgrey),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(KeepTogether([t, Spacer(1,5)]))

PB()

# ═══════════════════════════════════════════════════════════════════════════
H1("13.  Quick Reference Card")
S(4)
BD("The tables below are a compact cheat sheet. Once you are comfortable "
   "with the explanations in earlier sections, you can use this as a lookup table.")

H2("Navigation")
mk_table([
    ["Task","Linux / WSL","PowerShell","CMD"],
    ["Where am I?",        "pwd",               "pwd",              "cd"],
    ["Go into folder",     "cd foldername",     "cd foldername",    "cd foldername"],
    ["Go up one level",    "cd ..",             "cd ..",            "cd .."],
    ["Go to home",         "cd ~",              "cd $HOME",         "cd %USERPROFILE%"],
    ["Go to drive F:",     "cd /mnt/f",         "cd F:\\",          "F:\\"],
    ["List files",         "ls  or  ls -la",    "ls  or  dir",      "dir"],
], [0.22,0.26,0.26,0.26])

H2("File and Folder Operations")
mk_table([
    ["Task","Linux / WSL","PowerShell","CMD"],
    ["Create folder",   "mkdir name\nmkdir -p a/b/c",
     "mkdir name",                             "mkdir name"],
    ["Delete file",     "rm file.txt",
     "Remove-Item file.txt",                   "del file.txt"],
    ["Delete folder",   "rm -rf folder",
     "Remove-Item -Recurse -Force folder",     "rmdir /s /q folder"],
    ["Rename file",     "mv old new",
     "Rename-Item old new",                    "ren old new"],
    ["Copy file",       "cp src dst",
     "Copy-Item src dst",                      "copy src dst"],
    ["View file",       "cat file.txt",
     "Get-Content file.txt",                   "type file.txt"],
    ["Chain (if ok)",   "cmd1 && cmd2",
     "cmd1 ; cmd2",                            "cmd1 && cmd2"],
    ["Chain (always)",  "cmd1 ; cmd2",
     "cmd1 ; cmd2",                            "cmd1 & cmd2"],
], [0.22,0.26,0.26,0.26])

H2("WSL Commands (typed in PowerShell or CMD)")
mk_table([
    ["Command","What It Does"],
    ["wsl",               "Open a WSL bash terminal"],
    ["wsl --list",        "Show installed Linux distributions"],
    ["wsl --shutdown",    "Stop all WSL instances (releases file locks)"],
    ["wsl --version",     "Show WSL and kernel version"],
    ["exit",              "Leave WSL (typed inside WSL)"],
], [0.30, 0.70])

H2("apt Package Manager (typed in WSL)")
mk_table([
    ["Command","What It Does"],
    ["sudo apt update",                  "Refresh the package catalogue"],
    ["sudo apt install -y cmake gcc g++ make", "Install build tools"],
    ["sudo apt remove package",          "Uninstall a package"],
    ["apt search keyword",               "Search for a package"],
], [0.42, 0.58])

H2("CMake Build Commands (typed in WSL, inside ~/har_build)")
mk_table([
    ["Command","What It Does"],
    ['cmake "/mnt/f/.../project"',       "Configure: read CMakeLists.txt and prepare build files"],
    ["cmake --build .",                  "Build: compile all C source files"],
    ["cmake --build . -j4",              "Build using 4 CPU cores in parallel (faster)"],
    ["cmake --build . --clean-first",    "Delete old compiled files and rebuild everything"],
], [0.42, 0.58])

H2("Keyboard Shortcuts")
mk_table([
    ["Shortcut","What It Does","Works In"],
    ["Ctrl+C",      "Stop the currently running program", "All shells"],
    ["Up Arrow",    "Recall the previous command", "All shells"],
    ["Down Arrow",  "Go forward in command history", "All shells"],
    ["Tab",         "Autocomplete file/folder names", "All shells"],
    ["Ctrl+L",      "Clear the screen", "Linux/WSL, PowerShell"],
    ["Ctrl+A",      "Jump to beginning of the line", "Linux/WSL"],
    ["Ctrl+E",      "Jump to end of the line", "Linux/WSL"],
], [0.18, 0.52, 0.30])

S(8)
HR()
story.append(Paragraph(
    "Mohamed (matef517@gmail.com)  ·  OnDevice HAR FQT+RigL Master Thesis  ·  2026",
    PS("ft","Normal", fontSize=8, textColor=C_GREY, alignment=TA_CENTER)))

# ── Build PDF ───────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm,
    title="Shell Commands Reference — Beginner Edition",
    author="Mohamed",
)
doc.build(story)
print("Done:", OUT)
