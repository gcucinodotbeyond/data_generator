import jinja2
import json
import os
import random

# Setup
TEMPLATE_DIR = r"c:\Users\gcucino\Desktop\data_generator\DeterministicWalkers\generator\templates"
env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))
env.globals.update(random=random.random)

def to_json(obj, **kwargs):
    return json.dumps(obj, **kwargs)

def render(template_name, context):
    tmpl = env.get_template(template_name)
    try:
        return tmpl.render(**context, to_json=to_json)
    except Exception as e:
        return f"ERROR: {e}"

output = []
output.append("# Template Verification Report\n")

# 1. Search
output.append("## Search Template\n")
output.append("### Success (1 train)")
output.append("```json")
output.append(render("assistant/search.j2", {"category": "search_success", "n_trains": 1, "destination": "Milano", "first_dep": "10:00"}))
output.append("```\n")

output.append("### Success (3 trains)")
output.append("```json")
output.append(render("assistant/search.j2", {"category": "search_success", "n_trains": 3, "destination": "Roma", "first_dep": "08:30"}))
output.append("```\n")

output.append("### Empty")
output.append("```json")
output.append(render("assistant/search.j2", {"category": "search_empty", "destination": "Canicattì"}))
output.append("```\n")

output.append("### Ask Pax")
output.append("```json")
output.append(render("assistant/search.j2", {"category": "ask_passengers"}))
output.append("```\n")

output.append("### Disability Ack (Wheelchair)")
output.append("```json")
output.append(render("assistant/search.j2", {"category": "disability_ack", "disability_type": "wheelchair"}))
output.append("```\n")

# 2. Booking
output.append("## Booking Template\n")
output.append("### Seat Prompt")
output.append("```json")
output.append(render("assistant/booking.j2", {"category": "seat_prompt", "rudeness": "neutral"}))
output.append("```\n")

output.append("### Seat Ack (Window)")
output.append("```json")
output.append(render("assistant/booking.j2", {"category": "seat_ack", "seat_type": "window"}))
output.append("```\n")

output.append("### Class Prompt")
output.append("```json")
output.append(render("assistant/booking.j2", {"category": "class_prompt"}))
output.append("```\n")

output.append("### Class Ack")
output.append("```json")
output.append(render("assistant/booking.j2", {"category": "class_ack", "class_name": "Standard"}))
output.append("```\n")

output.append("### Seat Assignment")
output.append("```json")
output.append(render("assistant/booking.j2", {"category": "seat_assignment", "seats": "2A, 2B", "carriage": "4"}))
output.append("```\n")

output.append("### Handshake")
output.append("```json")
output.append(render("assistant/booking.j2", {"category": "handshake", "price": "50.00"}))
output.append("```\n")

output.append("### Ticket Handover")
output.append("```json")
output.append(render("assistant/booking.j2", {"category": "ticket_handover"}))
output.append("```\n")

# 3. Info
output.append("## Info Template\n")
output.append("### UI Action")
output.append("```json")
output.append(render("assistant/info.j2", {"category": "ui_action"}))
output.append("```\n")

output.append("### Show Info Train")
output.append("```json")
output.append(render("assistant/info.j2", {"category": "show_info_response", "target": "train", "status": "In orario"}))
output.append("```\n")

output.append("### QA Answer")
output.append("```json")
output.append(render("assistant/info.j2", {"category": "qa_answer", "answer": "I cani sono ammessi con trasportino."}))
output.append("```\n")

output.append("### Complaint Response")
output.append("```json")
output.append(render("assistant/info.j2", {"category": "complaint_response"}))
output.append("```\n")

# 4. Chitchat
output.append("## Chitchat Template\n")
output.append("### Greeting")
output.append("```json")
output.append(render("assistant/chitchat.j2", {"category": "greeting_response"}))
output.append("```\n")

output.append("### Farewell")
output.append("```json")
output.append(render("assistant/chitchat.j2", {"category": "farewell"}))
output.append("```\n")

with open("verification_report.md", "w", encoding="utf-8") as f:
    f.writelines(output)

print("Verification report written to verification_report.md")
