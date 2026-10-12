"""
FRIDAY AI — Code-to-Execution-to-Deployment Intelligence Service
Provides lifecycle stage detection, beginner-friendly execution guidance,
OS-aware command generation, troubleshooting diagnostics, and lab safety redirection.
"""

import re
from enum import Enum
from typing import Optional


class LifecycleStage(str, Enum):
    REQUIREMENT = "requirement"
    CODE_GEN = "code_generation"
    FILE_PLACEMENT = "file_placement"
    RUNTIME_SETUP = "runtime_setup"
    DEPENDENCY_INSTALL = "dependency_install"
    CONFIGURATION = "configuration"
    EXECUTION = "execution"
    TESTING_VERIFICATION = "testing_verification"
    TROUBLESHOOTING = "troubleshooting"
    PACKAGING = "packaging"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    SAFETY_REDIRECT = "safety_redirect"
    BEGINNER_MODE = "beginner_mode"
    STATE_ADVANCE = "state_advance"


def detect_lifecycle_intent(message: str, history: Optional[list[dict]] = None) -> LifecycleStage:
    """
    Detect the user's current lifecycle stage intent from their message and conversation context.
    """
    text = message.lower().strip()

    # 1. Safety check / Unauthorized target redirection
    unauthorized_patterns = [
        r"\bvictim\b",
        r"\bvictim's\b",
        r"\bwithout (?:them|him|her|anyone) knowing\b",
        r"\bunauthorized\b",
        r"\bhack (?:someone|somebody|my friend|my boss)\b",
        r"\bspy on\b",
        r"\bsteal credentials from someone\b",
    ]
    if any(re.search(pat, text) for pat in unauthorized_patterns):
        return LifecycleStage.SAFETY_REDIRECT

    # 2. Beginner mode trigger
    if re.search(r"\b(?:i am a beginner|i'm a beginner|complete beginner|explain everything|i don't understand|i dont understand|step by step)\b", text):
        return LifecycleStage.BEGINNER_MODE

    # 3. State advancement triggers (skipping completed steps)
    if re.search(r"\b(?:already created the folder|folder is created|created the directory|folder already exists|already made the folder)\b", text):
        return LifecycleStage.STATE_ADVANCE

    if re.search(r"\b(?:program is running|server is running|it is running|app is up|running now|it's running)\b", text):
        return LifecycleStage.STATE_ADVANCE

    # 4. Error / Troubleshooting triggers
    error_patterns = [
        r"\bmodulenotfounderror\b",
        r"\bno module named\b",
        r"\btraceback\b",
        r"\bexception\b",
        r"\berror\b",
        r"\bfailed to\b",
        r"\bcommand not found\b",
        r"\bnot recognized as an internal or external command\b",
        r"\bconnection refused\b",
        r"\beconnrefused\b",
        r"\baddress already in use\b",
        r"\bwhy isn't this working\b",
        r"\bwhy is not working\b",
    ]
    if any(re.search(pat, text) for pat in error_patterns):
        return LifecycleStage.TROUBLESHOOTING

    # 5. File placement triggers
    if re.search(r"\b(?:where do i put|where should i save|what do i do with this file|where does this file go|which folder)\b", text):
        return LifecycleStage.FILE_PLACEMENT

    # 6. Execution triggers
    execution_patterns = [
        r"\bhow do i run\b",
        r"\bhow to run\b",
        r"\bhow do i start\b",
        r"\bhow to start\b",
        r"\bhow do i execute\b",
        r"\bhow to execute\b",
        r"\brun this\b",
        r"\bstart this\b",
    ]
    if any(re.search(pat, text) for pat in execution_patterns):
        return LifecycleStage.EXECUTION

    # 7. Deployment / Transfer triggers
    deployment_patterns = [
        r"\bhow do i deploy\b",
        r"\bhow to deploy\b",
        r"\bhow do i install this on (?:my|a|an)\b",
        r"\bdeploy this to\b",
        r"\bput this on another (?:computer|machine|server|pc)\b",
        r"\buse this on another computer\b",
        r"\bdeploy (?:using|via) usb\b",
        r"\busb\b",
    ]
    if any(re.search(pat, text) for pat in deployment_patterns):
        return LifecycleStage.DEPLOYMENT

    # 8. Dependency / Runtime installation
    if re.search(r"\b(?:how do i install|how to install dependencies|pip install|npm install)\b", text):
        return LifecycleStage.DEPENDENCY_INSTALL

    # 9. Verification / Testing
    if re.search(r"\b(?:how do i test|how to test|verify|is it working)\b", text):
        return LifecycleStage.TESTING_VERIFICATION

    # 10. Documentation
    if re.search(r"\b(?:document|readme|runbook|setup guide)\b", text):
        return LifecycleStage.DOCUMENTATION

    return LifecycleStage.CODE_GEN


def get_stage_directive(stage: LifecycleStage, user_message: str) -> str:
    """
    Returns an explicit, high-priority operational directive for the LLM based on
    the detected lifecycle stage. This ensures adherence to the master rules.
    """
    text = user_message.lower()

    if stage == LifecycleStage.SAFETY_REDIRECT:
        return (
            "SAFETY & LAB REDIRECTION REQUIRED: The user mentioned a victim, unauthorized target, or unowned machine. "
            "DO NOT provide stealth deployment, covert persistence, or unauthorized access instructions. "
            "Instead, redirect the user to a controlled lab environment: 'To test this behavior safely, set up a dedicated "
            "virtual machine or isolated lab environment that you control (such as a local VirtualBox/VMware VM or Docker container)...' "
            "Then provide the complete, controlled lab deployment and monitoring workflow."
        )

    if stage == LifecycleStage.EXECUTION:
        return (
            "EXECUTION GUIDANCE MODE: The user is asking how to run previously generated code. "
            "DO NOT regenerate the code. Provide concise, beginner-friendly execution instructions: "
            "1. Project folder & filename where code belongs. "
            "2. Required runtime check (e.g., `python --version`). "
            "3. Exact terminal to open and directory navigation command (`cd ...`). "
            "4. Execution command (`python <filename>`). "
            "5. Expected output upon successful run."
        )

    if stage == LifecycleStage.TROUBLESHOOTING:
        if "modulenotfounderror" in text or "no module named" in text:
            return (
                "TROUBLESHOOTING (ModuleNotFoundError): Explain in beginner-friendly terms that Python cannot find the "
                "requested library because it is not installed. Identify the missing package, provide the exact installation command "
                "(`pip install <package>` or `pip install -r requirements.txt`), and instruct the user to re-run the script."
            )
        return (
            "TROUBLESHOOTING MODE: 1. Explain what the error means in beginner-friendly language. "
            "2. Identify the likely root cause. "
            "3. Give the smallest single corrective action. "
            "4. Ask the user to re-test. If the error message is ambiguous, ask the user to paste the complete error output."
        )

    if stage == LifecycleStage.BEGINNER_MODE:
        return (
            "BEGINNER MODE ACTIVATED: Assume zero prior command line or programming experience. "
            "Break down instructions into clear, numbered steps (STEP 1, STEP 2, STEP 3). "
            "Specify the exact terminal to open, exact commands to copy-paste, what each command does, and what successful output looks like. "
            "Avoid technical jargon and do not present walls of theoretical explanation before practical action."
        )

    if stage == LifecycleStage.STATE_ADVANCE:
        if "already created the folder" in text or "folder is created" in text or "created the directory" in text:
            return (
                "STATE ADVANCEMENT (Folder Exists): The user has confirmed the project folder is already created. "
                "DO NOT instruct them to create the folder again. Proceed immediately to the NEXT step: creating the required files "
                "and saving the code."
            )
        if "program is running" in text or "server is running" in text or "it is running" in text:
            return (
                "STATE ADVANCEMENT (Running): The user confirmed the application is currently running. "
                "DO NOT restart the setup or re-run the application. Proceed immediately to execution verification and testing "
                "(e.g., testing endpoints, curl commands, or browser verification)."
            )
        return "STATE ADVANCEMENT: Acknowledge the completed step and move immediately to the next action in the lifecycle."

    if stage == LifecycleStage.DEPLOYMENT:
        if "usb" in text:
            return (
                "DEPLOYMENT (USB Transfer vs Execution): Explain legitimate deployment via USB to a machine the user owns/controls. "
                "CRITICALLY DISTINGUISH TRANSFER FROM EXECUTION: Copying the files to a USB flash drive only transfers the code; "
                "it does not install or run it. Explain the steps on the destination machine: plug in USB, copy files to target directory, "
                "verify runtime, install dependencies, and execute."
            )
        if "linux" in text:
            return (
                "DEPLOYMENT (Linux Server): Provide a Linux deployment workflow for a server under your management: "
                "1. Transfer via Git or SCP/SFTP. "
                "2. Remote connection via SSH (`ssh user@server`). "
                "3. Setting up virtual environment (`python3 -m venv .venv` and `source .venv/bin/activate`). "
                "4. Installing dependencies (`pip install -r requirements.txt`). "
                "5. Running as a persistent background service (e.g., systemd service unit or tmux/screen). "
                "6. Verifying the service status (`systemctl status` or curl health check)."
            )
        if "windows" in text:
            return (
                "DEPLOYMENT (Windows PC): Provide a Windows deployment workflow for an owned PC: "
                "1. Project folder placement on the target PC. "
                "2. Runtime verification (`python --version`). "
                "3. Virtual environment creation & PowerShell execution policy note. "
                "4. Dependency installation. "
                "5. Running the script or configuring as a Scheduled Task/Service if background operation is desired. "
                "6. Verification."
            )
        return (
            "DEPLOYMENT GUIDANCE: Clearly distinguish LOCAL EXECUTION, TESTING, PACKAGING, TRANSFER, DEPLOYMENT, and PERSISTENCE. "
            "Provide the appropriate deployment lifecycle: BUILD → PACKAGE → TRANSFER → INSTALL DEPENDENCIES → CONFIGURE → RUN → VERIFY."
        )

    if stage == LifecycleStage.FILE_PLACEMENT:
        return (
            "FILE PLACEMENT GUIDANCE: Clearly state the exact filename and relative folder path where this code belongs. "
            "Show the minimal project directory tree and state the specific purpose of each file."
        )

    return ""
