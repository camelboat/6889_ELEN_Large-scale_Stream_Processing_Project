from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import sys
import json
import requests
import random

def results(request):
    context = {}
    return render(request, "result.html", context)


def getIframeLink(state_name):
    pool = [
        '<iframe width="100%" height="400px" src="https://datastudio.google.com/embed/reporting/1KKOd6Uxr2t62ARGJiiHRCc5HV-0wj_AN/page/eZHPB" frameborder="0" style="border:0" allowfullscreen></iframe>',
        '<iframe width="100%" height="400px" src="https://datastudio.google.com/embed/reporting/1fGzcEpVSGHl593CyuJG5wfoiOLvnhTMH/page/GfHPB" frameborder="0" style="border:0" allowfullscreen></iframe>',
        '<iframe width="100%" height="400px" src="https://datastudio.google.com/embed/reporting/1n-l887L05MiWmkNjo05EpVN28mVgXXs4/page/KfHPB" frameborder="0" style="border:0" allowfullscreen></iframe>',
        '<iframe width="100%" height="400px" src="https://datastudio.google.com/embed/reporting/1zZeaXXDfuYCmnaBVvg8QgsGjhqET8y9c/page/WXIPB" frameborder="0" style="border:0" allowfullscreen></iframe>'
    ]
    # [NY, CA, MI, TX]

    if state_name == 'New York':
        return pool[0]
    elif state_name == 'California':
        return pool[1]
    elif state_name == 'Michigan':
        return pool[2]
    elif state_name =='Texas':
        return pool[3]
    else:
        return pool[random.randint(0, 3)]


def state_details(request, state_name):
    context = {}
    context["state_detail"] = {
        "name": str(state_name),
        "hotspots": getIframeLink(state_name)
    }

    return render(request, "detail.html", context)