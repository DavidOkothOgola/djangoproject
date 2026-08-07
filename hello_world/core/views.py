from django.shortcuts import render


def index(request):
    context = {
        "title": "Dash",
        "headline": "Paid consultant chats with M-Pesa built in",
        "subheadline": (
            "Dash gives consultants a secure chat workspace where every session is timed, "
            "billed, and settled through M-Pesa or your preferred payment gateway."
        ),
        "features": [
            {
                "title": "Timed consultation rooms",
                "description": "Launch private chats, meter each minute, and keep client conversations organized.",
            },
            {
                "title": "M-Pesa collections",
                "description": "Collect deposits and session fees with familiar STK push payment flows.",
            },
            {
                "title": "Flexible payment gateway support",
                "description": "Accept cards and alternative payment methods alongside M-Pesa for global clients.",
            },
        ],
        "journey": [
            "Client selects a consultant and sees the live hourly rate.",
            "Dash collects payment through M-Pesa or a connected payment gateway.",
            "The timed chat starts instantly and the consultant is paid for every billable minute.",
        ],
    }
    return render(request, "index.html", context)
