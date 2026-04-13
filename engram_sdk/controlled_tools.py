from __future__ import annotations
from typing import Any, Dict, Optional
import structlog
from .global_data import get_global_data, ToolDefinition

logger = structlog.get_logger(__name__)

def process_raw_identification() -> str:
    """
    Thick function that pulls 'raw_input' from GlobalData, 
    extracts identity components, and writes them back.
    Zero arguments required from the model.
    """
    db = get_global_data()
    raw = db.get("raw_input")
    
    if not raw:
        return "Error: 'raw_input' not found in GlobalData."
    
    logger.info("processing_identity", raw_length=len(str(raw)))
    
    # Mock logic: Assume raw input is "Name <email@example.com>"
    try:
        if "<" in str(raw) and ">" in str(raw):
            name = str(raw).split("<")[0].strip()
            email = str(raw).split("<")[1].split(">")[0].strip()
        else:
            name = "Unknown"
            email = str(raw).strip()
            
        db.set("user_name", name)
        db.set("user_email", email)
        db.set("identity_verified", True)
        
        return f"Successfully extracted Name: {name}, Email: {email}"
    except Exception as e:
        return f"failed to process identity: {str(e)}"

def verify_security_clearance() -> str:
    """
    Checks 'user_email' in GlobalData against a mock security database
    and stores 'clearance_level' back in GlobalData.
    Zero arguments required from the model.
    """
    db = get_global_data()
    email = db.get("user_email")
    
    if not email:
        return "Error: 'user_email' not found in GlobalData. Identity must be processed first."
    
    # Mock security database lookup
    clearance = "Level 1 (Public)"
    if "admin" in email:
        clearance = "Level 5 (Superuser)"
    elif "staff" in email:
        clearance = "Level 3 (Staff)"
        
    db.set("clearance_level", clearance)
    return f"Security clearance verified for {email}: {clearance}"

def generate_access_report() -> str:
    """
    Compiles all identity and security data from GlobalData into a final report.
    Zero arguments required from the model.
    """
    db = get_global_data()
    data = db.all()
    
    required = ["user_name", "user_email", "clearance_level"]
    missing = [k for k in required if k not in data]
    
    if missing:
        return f"Error: Missing required data for report: {missing}"
        
    report = (
        f"ACCESS REPORT\n"
        f"-------------\n"
        f"Subject: {data['user_name']}\n"
        f"Identifier: {data['user_email']}\n"
        f"Clearance: {data['clearance_level']}\n"
        f"Status: VALIDATED\n"
    )
    
    db.set("final_report", report)
    return "Final access report generated and stored in GlobalData."

def scrub_sensitive_data() -> str:
    """
    Removes raw input and intermediate data from GlobalData to ensure privacy.
    Zero arguments required.
    """
    db = get_global_data()
    removed = []
    for key in ["raw_input", "temp_passphrase", "internal_id"]:
        if db.delete(key):
            removed.append(key)
    
    return f"Sensitive data scrubbed: {removed}"

# Tool Definitions for registration with zero/minimal schemas
PROCESS_IDENTITY_TOOL = ToolDefinition(
    name="process_raw_identification",
    description="Extracts name and email from 'raw_input' in GlobalData and stores them back. Requires 'raw_input' to be present.",
    input_schema={"type": "object", "properties": {}}
)

VERIFY_CLEARANCE_TOOL = ToolDefinition(
    name="verify_security_clearance",
    description="Assigns a clearance level based on 'user_email' in GlobalData. Requires 'user_email' to be present.",
    input_schema={"type": "object", "properties": {}}
)

GENERATE_REPORT_TOOL = ToolDefinition(
    name="generate_access_report",
    description="Generates a final text report from the collected GlobalData state. Requires identity and clearance to be present.",
    input_schema={"type": "object", "properties": {}}
)

SCRUB_DATA_TOOL = ToolDefinition(
    name="scrub_sensitive_data",
    description="Removes raw or temporary input from GlobalData for privacy compliance.",
    input_schema={"type": "object", "properties": {}}
)
