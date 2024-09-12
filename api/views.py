import json
from datetime import datetime
from datetime import timedelta

from django.utils import timezone
from django.http import JsonResponse

from .appSettings import appSettings
from api.whatsapp_api_handle import API

def whatsapp(request):
    if request.method == "POST":
        print("POST /api/whatsapp")
        API(json.loads(request.body.decode("utf-8")))
        return JsonResponse({"statusCode": 200, "message": "Message sent successfully."})
    else:
        return JsonResponse({"message": "Authorization required."})


def classroom(request):
    if request.method == "POST":
        print("POST /api/classroom")
        body = json.loads(request.body.decode("utf-8"))
        print(body)
        API(
            {
                "document": body,
                "document_type": "google_classroom_api",
                "from": f"{appSettings.admin_ids[0]}@s.whatsapp.net in {appSettings.classroom_group_id}@g.us",
                "message": {
                    "text": "./google_classroom_api",
                },
            }
        )
        return JsonResponse({"statusCode": 200, "message": "Notification sent successfully."})
    else:
        return JsonResponse({"message": "Authorization required."})


def reminder(request):
    if request.method == "POST":
        print("POST /api/reminder")
        body = json.loads(request.body.decode("utf-8"))

        print(body)

        distinct_body = []
        for reminder in body["reminders_notified"]:
            if reminder not in distinct_body:
                distinct_body.append(reminder)

        print(body)
        
        for reminder in body["reminders_notified"]:
            notes = json.loads(reminder["notes"])
            match str(reminder["application_id"]):
                case appSettings.reminders_api_classroom_id:
                    API(
                        {
                            "document": reminder,
                            "document_type": "reminder_api",
                            "from": f"{appSettings.admin_ids[0]}@s.whatsapp.net in {notes["sender"]}@g.us",
                            "message": {
                                "text": "./reminder_api",
                            },
                        }
                    )
                case appSettings.reminders_api_remind_id:
                    API(
                        {
                            "document": reminder,
                            "document_type": "reminder_api",
                            "from": f"{notes["sender"]}@s.whatsapp.net",
                            "message": {
                                "text": "./reminder_api",
                            },
                        }
                    )

        return JsonResponse({"statusCode": 200, "message": "Reminder sent successfully."})
    else:
        return JsonResponse({"message": "Authorization required."})
