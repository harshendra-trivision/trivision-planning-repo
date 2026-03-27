#
# Copyright (C) 2019 by frePPLe bv
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
from datetime import timedelta
from dateutil.parser import parse
import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core import management
from django.db import connections
from django.http import HttpResponse, HttpResponseServerError
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import TemplateView

from freppledb import __version__
from freppledb.common.report import getCurrency, getCurrentDate
from freppledb.common.models import Bucket, BucketDetail, Parameter
from freppledb.common.utils import sendEmail
from freppledb.input.models import (
    Location,
    Item,
    Customer,
    Demand,
    ItemSupplier,
    ItemDistribution,
    Operation,
    PurchaseOrder,
    Buffer,
    Supplier,
    ManufacturingOrder,
    DistributionOrder,
    OperationMaterial,
    OperationResource,
    Resource,
)

import logging

logger = logging.getLogger(__name__)

if "freppledb.forecast" in settings.INSTALLED_APPS:
    from freppledb.forecast.models import ForecastPlan


def parseDuration(v):
    d = v.strip().split(": ")
    args = len(d)
    try:
        if args == 0:
            return timedelta(0)
        elif args == 1:
            return timedelta(seconds=int(d[0]))
        elif args == 2:
            return timedelta(minutes=int(d[0]), seconds=int(d[1]))
        elif args == 3:
            return timedelta(hours=int(d[0]), minutes=int(d[1]), seconds=int(d[2]))
        elif args > 3:
            return timedelta(
                days=int(d[0]), hours=int(d[1]), minutes=int(d[2]), seconds=int(d[3])
            )
    except Exception:
        return timedelta(0)


def getWizardSteps(request, mode):
    try:
        versionnumber = __version__.split(".", 2)
        docurl = "%s/docs/%s.%s" % (
            settings.DOCUMENTATION_URL,
            versionnumber[0],
            versionnumber[1],
        )
    except Exception:
        docurl = "%s/docs/current" % settings.DOCUMENTATION_URL
    context = {
        "docroot": docurl,
        "prefix": request.prefix,
        "label_data": '<span class="badge" style="background: linear-gradient(135deg, #7B2D8E 0%, #9C27B0 100%); color: #fff; font-weight: 600; font-size: 0.7rem; padding: 0.4em 0.85em; border-radius: 6px; letter-spacing: 0.3px; box-shadow: 0 2px 6px rgba(123,45,142,0.25); text-transform: uppercase;">Data entry</span>',
        "label_config": '<span class="badge" style="background: linear-gradient(135deg, #2D004D 0%, #5C4670 100%); color: #fff; font-weight: 600; font-size: 0.7rem; padding: 0.4em 0.85em; border-radius: 6px; letter-spacing: 0.3px; box-shadow: 0 2px 6px rgba(45,0,77,0.25); text-transform: uppercase;">Configuration</span>',
        "label_action": '<span class="badge" style="background: linear-gradient(135deg, #DC2626 0%, #EF4444 100%); color: #fff; font-weight: 600; font-size: 0.7rem; padding: 0.4em 0.85em; border-radius: 6px; letter-spacing: 0.3px; box-shadow: 0 2px 6px rgba(220,38,38,0.25); text-transform: uppercase;">Action</span>',
        "label_check": '<span class="badge" style="background: linear-gradient(135deg, #A855F7 0%, #C084FC 100%); color: #fff; font-weight: 600; font-size: 0.7rem; padding: 0.4em 0.85em; border-radius: 6px; letter-spacing: 0.3px; box-shadow: 0 2px 6px rgba(168,85,247,0.25); text-transform: uppercase;">Check</span>',
        "label_analysis": '<span class="badge" style="background: linear-gradient(135deg, #059669 0%, #10B981 100%); color: #fff; font-weight: 600; font-size: 0.7rem; padding: 0.4em 0.85em; border-radius: 6px; letter-spacing: 0.3px; box-shadow: 0 2px 6px rgba(5,150,105,0.25); text-transform: uppercase;">Analysis</span>',
    }

    # Possible icons to display on the right hand side
    ICON_DONE = "fa-check-square-o"
    ICON_AVAILABLE = "fa-square-o"
    ICON_LOCK = "fa-lock"

    index = 0
    steps = []
    script = ""
    locked = False
    done = False

    # Welcome step
    if mode:
        welcome = """
           <p>Work towards the goal!</p>
           <p>New steps unlock only if you complete the previous one.</p>
           """
    else:
        welcome = """
        <style>
            .trivision-wizard-column {{
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                padding: 1.5rem;
                height: 100%%;
                background: #FFFFFF;
                border-radius: 16px;
                border: 1px solid rgba(123,45,142,0.08);
                box-shadow: 0 4px 20px rgba(123,45,142,0.06);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .trivision-wizard-column:hover {{
                transform: translateY(-4px);
                box-shadow: 0 12px 32px rgba(123,45,142,0.12);
                border-color: rgba(168,85,247,0.2);
            }}
            .trivision-icon-container {{
                position: relative;
                display: inline-block;
                margin-bottom: 1.25rem;
            }}
            .trivision-icon-circle {{
                width: 72px;
                height: 72px;
                border-radius: 50%%;
                border: none;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.6rem;
                color: #FFFFFF;
                background: linear-gradient(145deg, #7B2D8E 0%%, #A855F7 100%%);
                box-shadow: 0 6px 20px rgba(123,45,142,0.35);
                transition: all 0.3s ease;
            }}
            .trivision-icon-letter {{
                position: absolute;
                top: -4px;
                left: -4px;
                width: 26px;
                height: 26px;
                border-radius: 50%%;
                background: linear-gradient(135deg, #2D004D 0%%, #5C4670 100%%);
                color: #FFFFFF;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.7rem;
                font-weight: 700;
                box-shadow: 0 3px 8px rgba(45,0,77,0.4);
                font-family: 'Inter', -apple-system, sans-serif;
                border: 2px solid #FFFFFF;
            }}
            .trivision-wizard-column:hover .trivision-icon-circle {{
                transform: scale(1.08) rotate(3deg);
                box-shadow: 0 8px 28px rgba(168,85,247,0.4);
            }}
            .trivision-btn-primary {{
                background: linear-gradient(135deg, #7B2D8E 0%%, #A855F7 100%%) !important;
                color: #FFFFFF !important;
                border: none !important;
                border-radius: 25px !important;
                font-weight: 700 !important;
                padding: 0.6rem 1.75rem !important;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
                font-family: 'Inter', -apple-system, sans-serif;
                box-shadow: 0 4px 14px rgba(123,45,142,0.3) !important;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .trivision-btn-primary:hover, .trivision-btn-dropdown:hover {{
                background: linear-gradient(135deg, #2D004D 0%%, #7B2D8E 100%%) !important;
                transform: translateY(-3px) !important;
                box-shadow: 0 8px 24px rgba(123,45,142,0.4) !important;
            }}
            .trivision-btn-primary:active {{
                transform: translateY(-1px) !important;
            }}
            .trivision-dropdown-menu {{
                background-color: #FFFFFF !important;
                border-radius: 14px !important;
                box-shadow: 0 12px 40px rgba(123,45,142,0.15) !important;
                border: 1px solid rgba(156,39,176,0.1) !important;
                padding: 0.75rem !important;
                min-width: 180px;
                margin-top: 0.5rem !important;
            }}
            .trivision-dropdown-item {{
                color: #2D004D !important;
                background: transparent !important;
                border: none !important;
                text-align: center !important;
                font-weight: 600 !important;
                border-radius: 8px !important;
                padding: 0.65rem 1rem !important;
                transition: all 0.2s ease !important;
                margin-bottom: 0.35rem !important;
                box-shadow: none !important;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 0.8rem !important;
            }}
            .trivision-dropdown-item:hover {{
                color: #FFFFFF !important;
                background: linear-gradient(135deg, #7B2D8E 0%%, #A855F7 100%%) !important;
                transform: translateX(4px) !important;
            }}
            .trivision-dropdown-item:last-child {{
                margin-bottom: 0 !important;
            }}
            .trivision-row-card {{
                display: flex;
                align-items: center;
                background: #FFFFFF;
                border-radius: 14px;
                padding: 1.25rem 1.75rem;
                margin-bottom: 1rem;
                box-shadow: 0 4px 16px rgba(123,45,142,0.06);
                border: 1px solid rgba(156,39,176,0.08);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .trivision-row-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 28px rgba(123,45,142,0.12);
                border-color: rgba(168,85,247,0.2);
            }}
            .trivision-section-title {{
                font-family: 'Inter', -apple-system, sans-serif;
                font-weight: 800;
                font-size: 1.35rem;
                color: #2D004D;
                margin-bottom: 0.5rem;
                background: linear-gradient(135deg, #2D004D 0%%, #7B2D8E 100%%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
        </style>
        <div class="row pt-4 pb-3">
            <div class="col-auto justify-content-center d-flex w-100">
                <h1 class="trivision-section-title">Three ways to get started quickly</h1>
            </div>
        </div>
        <div class="row pb-4 gy-4 justify-content-center" id="wizard">

            <div class="col-md-4">
                <div class="trivision-wizard-column">
                    <div class="trivision-icon-container">
                        <div class="trivision-icon-circle"><i class="fa fa-hand-pointer-o"></i></div>
                        <div class="trivision-icon-letter">A</div>
                    </div>
                    <h2 style="font-family: 'Inter', -apple-system, sans-serif; font-size: 1rem; font-weight: 700; color: #2D004D; margin-bottom: 0.5rem;">Start with one item</h2>
                    <p style="font-family: 'Inter', -apple-system, sans-serif; color:#8B7A9E; font-size: 0.85rem; margin-bottom: 1.5rem; line-height: 1.5;">Begin exploring with a single product</p>
                    <div class="dropdown-center mt-auto">
                        <button class="btn btn-primary trivision-btn-primary" type="button" data-bs-toggle="dropdown" aria-expanded="false" style="min-width: 150px; font-size: 0.75rem;">
                            QUICKSTART <i class="fa fa-angle-down ms-2" style="font-size: 0.8rem;"></i>
                        </button>
                        <ul class="dropdown-menu trivision-dropdown-menu">
                            <li><a href="{prefix}/wizard/quickstart/forecast/" class="trivision-dropdown-item">FORECAST</a></li>
                            <li><a href="{prefix}/wizard/quickstart/production/" class="trivision-dropdown-item">PRODUCTION</a></li>
                        </ul>
                    </div>
                </div>
            </div>

            <div class="col-md-4">
                <div class="trivision-wizard-column">
                    <div class="trivision-icon-container">
                        <div class="trivision-icon-circle"><i class="fa fa-cloud-upload"></i></div>
                        <div class="trivision-icon-letter">B</div>
                    </div>
                    <h2 style="font-family: 'Inter', -apple-system, sans-serif; font-size: 1rem; font-weight: 700; color: #2D004D; margin-bottom: 0.5rem;">Upload more data</h2>
                    <p style="font-family: 'Inter', -apple-system, sans-serif; color:#8B7A9E; font-size: 0.85rem; margin-bottom: 1.5rem; line-height: 1.5;">Import your datasets via CSV or Excel</p>
                    <div class="dropdown-center mt-auto">
                        <button class="btn btn-primary trivision-btn-primary" type="button" data-bs-toggle="dropdown" aria-expanded="false" style="min-width: 150px; font-size: 0.75rem;">
                            UPLOAD <i class="fa fa-angle-down ms-2" style="font-size: 0.8rem;"></i>
                        </button>
                        <ul class="dropdown-menu trivision-dropdown-menu">
                            <li><a class="trivision-dropdown-item" href="{prefix}/wizard/load/forecast/">FORECAST</a></li>
                            <li><a class="trivision-dropdown-item" href="{prefix}/wizard/load/production/">PRODUCTION</a></li>
                        </ul>
                    </div>
                </div>
            </div>

            <div class="col-md-4">
                <div class="trivision-wizard-column">
                    <div class="trivision-icon-container">
                        <div class="trivision-icon-circle"><i class="fa fa-link"></i></div>
                        <div class="trivision-icon-letter">C</div>
                    </div>
                    <h2 style="font-family: 'Inter', -apple-system, sans-serif; font-size: 1rem; font-weight: 700; color: #2D004D; margin-bottom: 0.5rem;">Import from Odoo</h2>
                    <p style="font-family: 'Inter', -apple-system, sans-serif; color:#8B7A9E; font-size: 0.85rem; margin-bottom: 1.5rem; line-height: 1.5;">Sync directly with your ERP system</p>
                    <div class="dropdown-center mt-auto">
                        <a href="{prefix}/data/common/parameter/?noautofilter&name__contains=odoo" class="btn btn-primary trivision-btn-primary" style="min-width: 150px; font-size: 0.75rem; display: inline-flex; justify-content: center; align-items: center;">
                            CONNECT
                        </a>
                    </div>
                </div>
            </div>

        </div>
        """
    steps.append(
        {
            "index": index,
            "title": "Welcome",
            "icon": None,
            "locked": False,
            "content": welcome.format(**context),
        }
    )
    index += 1

    if "freppledb.forecast" in settings.INSTALLED_APPS and mode == "forecast":
        # Forecasting master data
        done = (
            Item.objects.using(request.database).exists()
            and Location.objects.using(request.database).exists()
            and Customer.objects.using(request.database).exists()
        )
        locked = not done
        steps.append(
            {
                "index": index,
                "title": "Step %s: Load master data: items, locations and customers"
                % index,
                "icon": ICON_AVAILABLE if not done else ICON_DONE,
                "locked": False,
                "content": """
         <p>Unsurprisingly, we start by loading some basic master data: items, locations and customers.</p>
         <p>You can either enter some sample records one by one, or (even better) load an Excel
         or CSV file you extract from another system.</p>
         
           
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/item/" class="text-decoration-underline" target="_blank">Load item data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/items.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/item.fcst.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load the items you want to forecast. You can do this in various ways:<br>
           <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span> Click on the plus sign to add data records one by one in form.<br>
           <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span> Edit data directly in the grid.<br>
           <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span> Click the up arrow icon to import a data file in Excel or CSV format. Have a look
           at the sample data to see how your data file should look like. You can even drag and drop your data
           file directly on the grid area <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span>.<br>
           <span class="circle">D</span> You can click the down arrow icon to export the existing data as a spreadsheet,
           make changes to the spreadsheet and then upload it again with the up arrow icon <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span>.</p>
            </div>
            <!--<div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load items')"><img src="/static/wizard/img/item.png" style="width: 200px"></a>
            </div> -->
        </div>
        

           
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/location/" class="text-decoration-underline" target="_blank">Load location data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/locations.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/location.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all locations from where items are sold to customers or where inventory is stored.<br>
           Location can be structured in a hierachical tree which allows intuitive
           navigation through the forecast data at aggregated levels.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load locations')"><img src="/static/wizard/img/location.png" style="width: 200px"></a>
            </div> -->
        </div>
        

           
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">3</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/customer/" class="text-decoration-underline" target="_blank">Load customer data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/customers.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/customer.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all customers for which you want to compute a forecast.<br>
           In a first model we recommend to keep the customer hierarchy simple: for instance,
           map all sales to a single aggregate customer.</p>
            </div>
            <!--<div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load customers')"><img src="/static/wizard/img/customer.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1

        # Forecasting sales history
        if not locked:
            done = Demand.objects.using(request.database).exists()
        steps.append(
            {
                "index": index,
                "title": "Step %s: Load historical sales data" % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>With the master data in place we can now proceed and load the sales order history.</p>
         <p>You will need to load the historical demand values for a period that is typically
         2 to 3 times as long as the future time window you want to forecast for. For instance, if you
         want to forecast for next year, you will need to load 2 to 3 years of historical sales data.
         If your demand presents seasonal patterns, you should also provide at least 3 past
         cycles so that we can correctly forecast the next cycle.
         The forecasting algorithms in frePPLe are able to generate a forecast with less historical
         data than the rules of thumb described above, but the statistical accuracy will then obviously
         be somewhat lower.</p>

         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/demand/" class="text-decoration-underline" target="_blank">Load sales order data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/sales-orders.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/salesorder.fcst.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all sales orders for the time window described above.<br>
           As the majority of these orders will already have been shipped, their status
           be "closed". Overdue backlog orders can be loaded with the status "open".<br>
           Unless the number of sales orders exceeds 2 million, we recommend to load them
           directly. For larger data volumes you might consider aggregating the data per time bucket.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load sales orders')"><img src="/static/wizard/img/salesorder.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1
        if not locked:
            locked = not done

        # Forecasting generate plan
        if not locked:
            done = ForecastPlan.objects.using(request.database).exists()
        parameter_forecast_calendar = Parameter.getValue(
            "forecast.calendar", request.database, None
        )
        parameter_forecast_horizonfuture = int(
            Parameter.getValue("forecast.Horizon_future", request.database, "365")
        )
        parameter_currentdate = Parameter.getValue(
            "currentdate", request.database, "now"
        )
        steps.append(
            {
                "index": index,
                "title": "Step %s: Calculate statistical forecast" % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>Almost there! First, let's configure a few important parameters so
         that we can compute the statistical forecast for you.</p>

         

         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_config}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/common/parameter/?name=forecast.calendar" class="text-decoration-underline" target="_blank">Configure the forecasting time bucket size</a></b>:</p>
         <p>Forecast values are computed by time bucket.<br>
         You need to configure what time bucket size you wish to use.</p>
         <div class="form-check ps-5 mb-2">
           <input class="form-check-input" type="radio" id="fcstbckt_month" name="fcstbckt" data-forecastbucketsize="month"
         """.format(
                    **context
                )
                + (
                    ' checked="checked"'
                    if parameter_forecast_calendar == "month"
                    else ""
                )
                + """><label for="fcstbckt_month" class="form-check-label">Monthly</label>
         </div>
         <div class="form-check ps-5 mb-3">
           <input class="form-check-input" type="radio" id="fcstbckt_week" name="fcstbckt" data-forecastbucketsize="week"
         """.format(
                    **context
                )
                + (
                    ' checked="checked"'
                    if parameter_forecast_calendar == "week"
                    else ""
                )
                + '''><label for="fcstbckt_week" class="form-check-label">Weekly</label>
         </div>
         <p class=mt-3">You can always review and update your choice with the parameter "forecast.calendar"
         in the <a href="{prefix}/data/common/parameter/" class="text-decoration-underline" target="_blank">parameter table</a>
         (available in the "admin" menu).</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        

         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_config}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/common/parameter/?name=forecast.Horizon_future" class="text-decoration-underline" target="_blank">Configure the forecasting horizon</a></b>:</p>
         <p>You also need to configure how far in the future you wish to forecast for:<br>
         <div class="ps-5 mt-2">
         <input class="form-control d-inline w-auto" style="width:20em" size="10" value="'''.format(
                    **context
                )
                + str(parameter_forecast_horizonfuture)
                + '''" data-parameter="forecast.Horizon_future"> days</div></p>
         <p>You can always review and update your choice with the parameter "forecast.Horizon_future"
         in the <a href="{prefix}/data/common/parameter/" class="text-decoration-underline" target="_blank">parameter table</a>
         (available in the "admin" menu).</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        

         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">3</span>{label_config}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/common/parameter/?name=forecast.currentdate" class="text-decoration-underline" target="_blank">Configure the current date</a></b>:</p>
         <p>In normal situations you'll want to compute the forecast starting from today onwards.<br>
         When your dataset is not recent you may want to step back to a moment in the past, and simulate
         generating a forecast from that moment onwards.</p>
         <p>Specify here the current date (in the format YYYY-MM-DD HH:MM:SS), or leave the default
         value "now" to use the system clock.<br>
         <div class="ps-5 mt-2">
         <input class="form-control d-inline w-auto" style="width:20em" size="17" value="'''.format(
                    **context
                )
                + str(parameter_currentdate)
                + """" data-parameter="currentdate"></div></p>
         <p>You can always review and update your choice with the parameter "currentdate"
         in the <a href="{prefix}/data/common/parameter/" class="text-decoration-underline" target="_blank">parameter table</a>
         (available in the "admin" menu).</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        

         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">4</span>{label_action}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/execute/" class="text-decoration-underline" target="_blank">Generate statistical forecast</a></b>:</p>
         <p>You can now compute the first statistical forecast.</p>
         <p>Open the <a href="{prefix}/execute/">execution screen</a> (available in the "admin" menu) and select
         the "generate plan" <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span> task. Make sure the option "generate forecast"
         <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span>is checked.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span> Launch the task and wait for it to complete. <span class="circle">D</span></p>
         <p>Whenever you change any of the intput data, you will need to come back here to recompute the forecast.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Generate statistical forecast')"><img src="/static/wizard/img/generate_forecast.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        script += (
            '''
         $("input[data-forecastbucketsize]").on('change', function(event) {
         $.ajax({
           type: 'POST',
           url: "'''
            + request.prefix
            + """/api/common/parameter/",
           data: {
             name: "forecast.calendar",
             value: $(this).attr("data-forecastbucketsize")
             }
           });
       });
      """
        )
        index += 1
        if not locked:
            locked = not done

        # Forecasting - review results
        steps.append(
            {
                "index": index,
                "title": "Step %s: Review results" % index,
                "icon": ICON_LOCK if locked else None,
                "locked": locked,
                "content": """
         <p>Now that the forecast has been computed, let's take some time to visit the main screens to
         review and update the results.</p>
         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_analysis}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/forecast/editor/" class="text-decoration-underline" target="_blank">Review forecast editor</a></b><br>
         <p>The <a href="{prefix}/forecast/editor/" class="text-decoration-underline" target="_blank">forecast editor</a> (available
         in the "sales" menu) is the main screen for reviewing the results.<p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span> Select a combination of item + location + customer in the top pane, and
         review the details in the bottom pane.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span> You can override the forecast proposed by the system. If you edit at a
         higher level the value is distributed automatically to all child levels.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span> You can adjust the sales history to adjust for exceptional demands.</p>
         <p><span class="circle">D</span> You can switch from units to monetary value.</p>
         <p><span class="circle">E</span> You can also visualize the report in different time bucket sizes.</p>
         </p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Forecast editor')"><img src="/static/wizard/img/forecast_editor.png" style="width: 200px"></a>
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_analysis}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><a href="{prefix}/forecast/" class="text-decoration-underline" target="_blank"><b>Review forecast report</b></a></p>
         <p>The <a href="{prefix}/forecast/" class="text-decoration-underline" target="_blank">forecast report</a> (available in the "sales" menu)
         is handy for going through a larger list of forecasts.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span> In this screen you can easily export forecast data as a spreadsheet.<p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span> You can also upload an Excel spreadsheet with forecast values from your sales team.</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Forecast report')"><img src="/static/wizard/img/forecast_report.png" style="width: 200px"></a>
            </div>
        </div>
        
         <p class="mt-3">Congratulations! You are now able to use the forecasting capabilities of frePPLe.</p>
         """.format(
                    **context
                ),
            }
        )
        index += 1

        # Forecasting - advanced features
        steps.append(
            {
                "index": index,
                "title": "Bonus: Advanced forecasting functionality",
                "icon": ICON_LOCK if locked else None,
                "locked": locked,
                "content": """
         <p>With the basics under your belt, you are ready to dig into some more advanced
         modeling and configuration topics.</p>
         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/videos/demand-forecasting/filter-outliers.html?highlight=outlier" class="text-decoration-underline" target="_blank">Outlier detection</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p>Exceptional one-off sales can seriously impact the accuracy of the forecast.
         FrePPLe provides mechanism to automatically detect and filter them out.</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/forecasting/forecast-method" class="text-decoration-underline" target="_blank">Forecasting methods</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p>This example model digs into the forecasting algorithms and their configuration.</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/forecasting/middle-out-forecast" class="text-decoration-underline" target="_blank">Middle-out forecasting</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p>The statistical forecast is computed by default at the lowest level in the
         hierarchies. In some situations, it's more appropriate to calculate the forecast at a higher level
         to achieve more accurate results.</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/forecasting/forecast-netting" class="text-decoration-underline" target="_blank">Forecast netting</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p>Demand in the near future mostly consists of customer sales orders. Demand far out in the
         future consists mostly of forecast. In many industries, both sales and forecast
         will coexist in the same time bucket.</p>
         <p>The forecast netting (aka forecast consumption) subtracts the sales orders from the
         forecast to avoid double-planning the same demand.</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         """.format(
                    **context
                ),
            }
        )
        index += 1
    if mode == "production":
        # Production master data
        done = (
            Item.objects.using(request.database).exists()
            and Location.objects.using(request.database).exists()
            and Customer.objects.using(request.database).exists()
        )
        locked = not done
        steps.append(
            {
                "index": index,
                "title": "Step %s: Load master data: items, locations and customers"
                % index,
                "icon": ICON_DONE if done else ICON_AVAILABLE,
                "locked": False,
                "content": """
         <p>It won't be a surprise that we start by loading some basic master data: items, locations and customers.</p>
         <p>You can either enter some sample records one by one, or (even better) load an Excel
         or CSV file you extract from some existing database</p>

         
           
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/item/" class="text-decoration-underline" target="_blank">Load item data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/items.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/item.mfg.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all items: end items sold to customers, intermediate items in the production process and
           raw materials purchased from suppliers.</p>
           <p> Data can be loaded by:<br>
           <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span> Click on the plus sign to add data records one by one in form.<br>
           <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span> Edit data directly in the grid.<br>
           <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span> Click the up arrow icon to import a data file in Excel or CSV format. Have a look
           at the sample data to see how your data file should look like. You can even drag and drop your data
           file directly on the grid area <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span>.<br>
           <span class="circle">D</span> You can click the down arrow icon to export the existing data as a spreadsheet,
           make changes to the spreadsheet and then upload it again with the up arrow icon <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span>.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load items')"><img src="/static/wizard/img/item.png" style="width: 200px"></a>
            </div> -->
        </div>
        

           
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/location/" class="text-decoration-underline" target="_blank">Load location data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/locations.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/location.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all locations from where items are sold to customers or where inventory is stored.</p>
            </div>
            <!--<div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load locations')"><img src="/static/wizard/img/location.png" style="width: 200px"></a>
            </div> -->
        </div> 
        

           
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">3</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/customer/" class="text-decoration-underline" target="_blank">Load customer data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/customers.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/customer.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all customers to which products are sold.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load customers')"><img src="/static/wizard/img/customer.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1

        # Production - sales orders
        if not locked:
            done = Demand.objects.using(request.database).exists()
        steps.append(
            {
                "index": index,
                "title": "Step %s: Load sales order data" % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>With the master data in place we can now proceed and load the sales order book.</p>

         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/demand/" class="text-decoration-underline" target"_blank">Load sales order data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/sales-orders.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/salesorder.mfg.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           For planning we only need the open sales orders, the remaining quantity to ship
           and the delivery date expected by customers.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load sales orders')"><img src="/static/wizard/img/salesorder.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1
        if not locked:
            locked = not done

        # Production - define production operations
        if not locked:
            done = (
                Operation.objects.using(request.database).exists()
                and OperationMaterial.objects.using(request.database).exists()
            )
        steps.append(
            {
                "index": index,
                "title": "Step %s: Define operations and bill of material" % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>Before moving on please read
         <a href="{docroot}/modeling-wizard/concepts.html" class="text-decoration-underline" target="_blank">this page</a>.
         You'll learn how the supply chain network is built up with operations
         that are connecting buffers.<p>

         <p>There are 2 common model structures:
         <ul>
         <li style="list-style: disc">
         <p><img style="width: 200px; float: left" src="/static/wizard/img/operation_single.png">
         <b>Models with single operation production</b><br>
         These models use a single operation to produce an item.
         </li>
         <li style="list-style: disc; clear: both">
         <img style="width: 200px; float: left" src="/static/wizard/img/operation_routing.png">
         <b>Models with multiple steps per operation</b><br>
         The operation of an item is modeled as a sequence of step operations that are grouped
         together in a routing.
         </li>
         </ol>

         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/operation/" class="text-decoration-underline" target="_blank">Load operation data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/manufacturing-bom/operations.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/operation.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Defines the operations and their duration.</p>
           <p>An operation of type "routing" defines the producion routings. Extra records
           defines the step operations and their duration.</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load operations')"><img src="/static/wizard/img/operation.png" style="width: 200px"></a>
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/operationmaterial/" class="text-decoration-underline" target="_blank">Load operation material data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/manufacturing-bom/operation-materials.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/operationmaterial.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Defines the materials produced and consumed by the operations.</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load operation materials')"><img src="/static/wizard/img/operationmaterial.png" style="width: 200px"></a>
            </div>
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1
        if not locked:
            locked = not done

        # Production - item supplier
        if not locked:
            done = ItemSupplier.objects.all().using(request.database).exists()
        steps.append(
            {
                "index": index,
                "title": "Step %s: Define suppliers and lead time for procured items"
                % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>In this step you define all suppliers and the lead times for purchasing items from them.</p>

         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/supplier/" class="text-decoration-underline" target="_blank">Load supplier data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/purchasing/suppliers.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/supplier.mfg.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all the suppliers from which you can purchase items.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load suppliers')"><img src="/static/wizard/img/supplier.png" style="width: 200px"></a>
            </div> -->
        </div>
        
           
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/itemsupplier/" class="text-decoration-underline" target="_blank">Load item supplier data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/purchasing/item-suppliers.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/itemsupplier.mfg.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>In this table you define which item can be purchased from which supplier.</p>
            </div>
            <!--<div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load item suppliers')"><img src="/static/wizard/img/itemsupplier.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1
        if not locked:
            locked = not done

        # Production - review the network
        if not locked:
            done = (
                Operation.objects.all().using(request.database).exists()
                or ItemSupplier.objects.all().using(request.database).exists()
            )
        steps.append(
            {
                "index": index,
                "title": "Step %s: Review the supply network" % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>All right, it's time to for a first checkpoint. We'll verify the supply chain structure
         you have modeled in the previous steps.</p>
         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_check}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b>Review the supply path of some sales orders</b></p>
         <p>Go to the <a href="{prefix}/data/input/demand/" class="text-decoration-underline" target="_blank">sales order list</a>
         and click the triangle icon <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span> to investigate some example sales orders.</p>
         <p>Select the "supply path" tab <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span>, and study the graph.</p>
         <p>On the far right you find the end items, and moving towards the left we move to operations
         deeper in the bill of material. On the far left we find the raw materials
         and their purchasing operations.</p>
         <p>If the path is complete and correct, congratulations! You have successfully
         understood and implemented the previous steps.</p>
         <p>If your paths are broken or contain cycles, you will need to review and correct the operations
         to get the supply path correct.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Sales order drilldown')"><img src="/static/wizard/img/salesorder_drilldown.png" style="width: 200px"></a>
         <br><br>
         <a href="#" onclick="showModalImage(event, 'Sales order supply path')"><img src="/static/wizard/img/supplypath_mfg.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1

        # Production - generate unconstrained plan
        parameter_populateForecastTable = Parameter.getValue(
            "forecast.populateForecastTable", request.database, "true"
        )
        steps.append(
            {
                "index": index,
                "title": "Step %s: Generate and review the unconstrained MRP-plan"
                % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>We'll generate a first unconstrained plan and review the list of proposed manufacturing orders and
         purchase orders.</p>
         

         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_config}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/common/parameter/?name=forecast.populateForecastTable" class="text-decoration-underline" target="_blank">Enable or disable the use of forecast</a></b>:</p>
         <div class="form-check ps-5">
           <input class="form-check-input" id="fcst_auto" type="radio" name="fcstbckt" data-parameter="forecast.populateForecastTable" data-parameter-value="true"
           """.format(
                    **context
                )
                + (
                    ' checked="checked"'
                    if parameter_populateForecastTable.lower() == "true"
                    else ""
                )
                + """>
           <label class="form-check-label" for="fcst_auto">Automatically populate the <a href="{prefix}/data/forecast/forecast/" class="text-decoration-underline" target="_blank">forecast table</a>.<br>
           Use this option if you want to plan forecast.
           </label>
         </div>
         <div class="form-check ps-5">
           <input class="form-check-input" type="radio" id="fcst_man" name="fcstbckt" data-parameter="forecast.populateForecastTable" data-parameter-value="false"
           """.format(
                    **context
                )
                + (
                    ' checked="checked"'
                    if parameter_populateForecastTable.lower() != "true"
                    else ""
                )
                + """>
           <label class="form-check-label" for="fcst_man">Do NOT populate the <a href="{prefix}/data/forecast/forecast/" class="text-decoration-underline" target="_blank">forecast table</a> automatically.<br>
           Use this option if you do NOT want to plan forecast.
           </label>
         </div>
         <p>You can always update your choice later with the parameter "forecast.populateForecastTable"
         in the <a href="{prefix}/data/common/parameter/" class="text-decoration-underline" target="_blank">parameter table</a> (available in the "admin" menu).</p>
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        

         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_action}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/execute/" class="text-decoration-underline" target="_blank">Generate an unconstrained plan</a></b></p>
         <p>You can now compute the first plan.</p>
         <p>Open the <a href="{prefix}/execute/">execution screen</a> (available in the "admin" menu) and select
         the "generate plan" task. Make sure the "generate supply plan" option <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span>
         is checked, and make sure to generate an unconstrained plan <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span>.<p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span> Launch the task and wait for it to complete. <span class="circle">D</span></p>
         <p><b>Whenever you change any of the input data, you will need to come back to this screen to recompute the plan.</b></p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Generate unconstrained plan')"><img src="/static/wizard/img/generate_unconstrained.png" style="width: 200px"></a>
            </div> -->
        </div>
        

         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">3</span>{label_analysis}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/manufacturingorder/" class="text-decoration-underline" target="_blank">Load Manufacturing order data</a></b></p>
         <p>The <a href="{prefix}/data/input/manufacturingorder/" class="text-decoration-underline" target="_blank">manufacturing order</a> screen
         (available in the "Manufacturing" menu) gives an overview of all manufacturing orders.
         The plan generated in the previous step created a set of proposed manufacturing
         orders to deliver your sales orders.</p>
         <p>If the list is empty, it is very likely you made a mistake in any of the
         previous steps. You should review the supply path of the sales orders again.</p>
         <p>If the list isn't empty, you can review that the timing, duration and quantity
         of the proposed manufacturing orders is matching your expectations. The result will
         match a textbook <a href="https://en.wikipedia.org/wiki/Material_requirements_planning" class="text-decoration-underline" target="_blank">MRP explosion</a>.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Manufacturing orders')"><img src="/static/wizard/img/manufacturingorder.png" style="width: 200px"></a><br>
            </div> -->
        </div>
        

         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">4</span>{label_analysis}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/purchaseorder/" class="text-decoration-underline" target="_blank">Load purchase order data</a></b></p>
         <p>The purchase order report (available in the "purchasing" menu) gives an overview of all
         purchase orders. The plan generated in the previous step created a set of
         proposed purchase orders to meet your sales orders.</p>
         <p>If the list is empty, it is very likely you made a mistake in any of the
         previous steps. You should review the supply path of the sales orders again.</p>
         <p>If the list isn't empty, you can review that the timing, duration and quantity
         of the proposed purchase orders is matching your expectations. The result will
         match a classic textbook <a href="https://en.wikipedia.org/wiki/Material_requirements_planning" class="text-decoration-underline" target="_blank">MRP explosion</a>.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Purchase orders')"><img src="/static/wizard/img/purchaseorder.png" style="width: 200px"></a><br>
            </div> -->
        </div>
        
         """.format(
                    **context
                ),
            }
        )
        index += 1
        if not locked:
            locked = not done

        # Production - load inventories, open PO and open MO
        if not locked:
            done = (
                Buffer.objects.all().using(request.database).exists()
                or PurchaseOrder.objects.all()
                .using(request.database)
                .filter(status="confirmed")
                .exists()
                or ManufacturingOrder.objects.all()
                .using(request.database)
                .filter(status="confirmed")
                .exists()
            )
        steps.append(
            {
                "index": index,
                "title": "Step %s: Load inventories, open purchase orders and work-in-progress manufacturing orders"
                % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>The plan in of the previous steps started with an empty factory and empty inventories.
         A correct plan obviously needs to consider the current stock and all purchase orders and
         manufacturing orders that are already ongoing or confirmed to start.</p>
         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/buffer/" class="text-decoration-underline" target="_blank">Load inventory data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/master-data/buffers.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/buffer.mfg.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load the current stock of all items. If the stock is 0, no record is required.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load on hand inventory')"><img src="/static/wizard/img/buffer.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/purchaseorder/" class="text-decoration-underline" target="_blank">Load purchase order data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/purchasing/purchase-orders.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/purchaseorder.mfg.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all purchase orders that you have already opened with suppliers.<br>
           The status field of the records should be "confirmed" to seperate them from the
           proposed purchase orders that were generated in the previous step.</p>
           <p>This table is thus used both as input and output.</p>
            </div>
            <!--<div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load purchase order data')"><img src="/static/wizard/img/purchaseorder.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">3</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/manufacturingorder/" class="text-decoration-underline" target="_blank">Load manufacturing order data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/manufacturing-bom/manufacturing-orders.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/manufacturingorder.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all manufacturing orders already released to the shop floor as work-in-progress.<br>
           The status field of the records should be "confirmed" to seperate them from the
           proposed manufacturing orders that were generated in the previous step.</p>
           <p>This table is thus used both as input and output.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load manufacturing order data')"><img src="/static/wizard/img/manufacturingorder.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1

        # Production - resources
        if not locked:
            done = OperationResource.objects.all().using(request.database).exists()
        steps.append(
            {
                "index": index,
                "title": "Step %s: Define resources and capacity consumption" % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>Let's add some capacity constraints.</p>
         <p>FrePPLe has different resource types (see
         <a class="text-decoration-underline" href="{docroot}/examples/resource/resource-type.html" target="_blank">here</a>
         for more detail). The most common types are:</p>
         <ul>
         <li style="list-style: disc">
         <p><img style="width: 200px; float: left" src="/static/wizard/img/resource-default.png">
         <b>"default"</b>: for a resource with a continuous representation of capacity.<br>
         This resource model is typically used for short-term detailed planning and scheduling.</p>
         </li>
         <li style="list-style: disc; clear: both">
         <p><img style="width: 200px; float: left" src="/static/wizard/img/resource-time-buckets.png">
         <b>"bucket_week" / "bucket_month"</b>: for a resource with capacity is expressed
         as available resource-hours per time bucket.<br>
         This resource model is typically used for mid-term master planning and rough cut
         capacity planning.</p>
         </li>
         </ul>
         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/resource/" class="text-decoration-underline" target="_blank">Load resource data</a></b>
             &nbsp;&nbsp;
             <a href="{docroot}/modeling-wizard/manufacturing-capacity/resources.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             &nbsp;&nbsp;
             <a href="/static/wizard/sample_data/resource.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>Load all resources.<br>
           A resource models a machine, a group of machines, an operator, a group of operators,
           or other capacity constraints.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load resource data')"><img src="/static/wizard/img/resource.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_data}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/operationresource/" class="text-decoration-underline" target="_blank">Load operation resource data</a></b>
             <a href="{docroot}/modeling-wizard/manufacturing-capacity/operation-resources.html" target="_blank">
             <i class="fa fa-book fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Documentation"></i>
             </a>
             <a href="/static/wizard/sample_data/operationresource.xlsx">
             <i class="fa fa-file-excel-o fa-2x" aria-hidden="true" data-bs-toggle="tooltip" title="Sample data in Excel format"></i>
             </a>
           </p>
           <p>This table associates each operation with the resources it utilizes.</p>
            </div>
            <!--<div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Load operation resource data')"><img src="/static/wizard/img/operationresource.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1
        if not locked:
            locked = not done

        # Production - generate plan
        if not locked:
            done = (
                PurchaseOrder.objects.all()
                .using(request.database)
                .filter(status="proposed")
                .exists()
                or ManufacturingOrder.objects.all()
                .using(request.database)
                .filter(status="proposed")
                .exists()
            )
        steps.append(
            {
                "index": index,
                "title": "Step %s: Generate a constrained plan" % index,
                "icon": ICON_LOCK if locked else ICON_DONE if done else ICON_AVAILABLE,
                "locked": locked,
                "content": """
         <p>You can now generate a more realistic plan.</p>
         <p>The unconstrained plan you generated earlier doesn't respect constraints: it will
         plan in the past and overload resources. It does plan all the demands on time.</p>
         <p>The constrained plan generated in this step will respect all the capacity, material
         availability, and procurement lead times. In case of lead time or capacity shortages,
         demands will be planned late.</p>
         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_action}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/execute/" class="text-decoration-underline" target="_blank">Generate constrained plan</a></b></p>
         <p>Navigate to the <a href="{prefix}/execute/" class="text-decoration-underline">execution screen</a> (available in the "admin"
         menu) and select the "generate plan" task <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span>. Make sure the options "generate supply
         plan" and "constrained plan" <span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span> are both checked.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span> Launch the task and wait for it to complete. <span class="circle">D</span></p>
         <p><b>Whenever you change any of the input data, you will need to come back here to regenerate the plan.</b></p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Generate constrained plan')"><img src="/static/wizard/img/generate_constrained.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
         """.format(
                    **context
                ),
            }
        )
        index += 1

        # Production - review results
        steps.append(
            {
                "index": index,
                "title": "Step %s: Review results" % index,
                "icon": ICON_LOCK if locked else None,
                "locked": locked,
                "content": """
         <p>A number of new screens are ready to be explored now!</p>
         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">1</span>{label_analysis}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/resource/" class="text-decoration-underline" target="_blank">Capacity report</a></b></p>
         <p>This report visualizes the utilization of all resources per time bucket.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span> The results can be displayed as a graph or as a table. You can click on
         cells in the table or buckets in the graph to get more detailed information.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span> You can adjust the time buckets and horizon of the report.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span> The down arrow icon allows to export the results in an
         Excel spreadsheet.</p>
         <p><span class="circle">D</span> In all reports you can customize which fields to display and
         their order.</p>
         <td style="text-align: center">
         <!-- <a href="#" onclick="showModalImage(event, 'Capacity report')"><img src="/static/wizard/img/resourcereport.png" style="width: 200px"></a> -->
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">2</span>{label_analysis}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/data/input/demand/" class="text-decoration-underline" target="_blank">Sales order</a></b></p>
         <p>At the start of the planning run, you loaded the sales orders in frePPLe. The constrained
         planning run you have just completed has 1) computed the planned delivery date for all sales
         orders and 2) collected the reasons why a certain demand was planned short or late.</p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">A</span> Review the list of
         <a href="{prefix}/data/input/demand/" class="text-decoration-underline" target="_blank">sales orders</a> and
         sort on the delay field to find some sales orders that can't be delivered on time.<p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">B</span> Click on the triangle icon next to a demand to drill into its details.<p>
         <p><span style="display:inline-flex; align-items:center; justify-content:center; width:1.4em; height:1.4em; border-radius:50%; background:linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); color:#fff; font-size:0.75em; font-weight:700; box-shadow:0 2px 6px rgba(123,45,142,0.3); margin-right:0.3em; vertical-align:middle;">C</span> The "plan" tab shows all operations planned to deliver the order.<p>
         <p><span class="circle">D</span> The "why short or late" tab shows all constraints causing lateness
         in the delivery of the order.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Sales order drilldown')"><img src="/static/wizard/img/salesorder_analysis.png" style="width: 200px">
                </a>
                <br><br>
                <a href="#" onclick="showModalImage(event, 'Gantt plan editor')"><img src="/static/wizard/img/salesorder_why_short_or_late.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;">3</span>{label_analysis}
            </div>
            <div style="flex: 1; color:#5C4670;">
                <p><b><a href="{prefix}/buffer/" class="text-decoration-underline" target="_blank">Inventory report</a></b></p>
         <p>This report visualizes the planned inventory for all item-locations per time bucket.</p>
            </div>
            <!-- <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                <a href="#" onclick="showModalImage(event, 'Inventory report')"><img src="/static/wizard/img/inventoryreport.png" style="width: 200px"></a>
            </div> -->
        </div>
        
         <p>Congratulations! You are now able to use the production planning capabilities of frePPLe.</p>
         """.format(
                    **context
                ),
            }
        )
        index += 1

        # Production - advanced features
        steps.append(
            {
                "index": index,
                "title": "Bonus: Advanced production planning functionality",
                "icon": ICON_LOCK if locked else None,
                "locked": locked,
                "content": """
         <p>With the basics under your belt, you are ready to dig into some more advanced
         modeling and configuration topics.</p>
         
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/modeling-wizard/common-modeling-mistakes.html" class="text-decoration-underline" target="_blank">Common mistakes</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                Learn about the most common gotchas and mistakes made by first-time users.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/calendar/calendar-working-hours.html" class="text-decoration-underline" target="_blank">Working&nbsp;hours</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                Modeling working hours, shifts and holidays is required to get a realistic plan.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/operation/operation-type.html" class="text-decoration-underline" target="_blank">Operation&nbsp;types</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                This example model demonstrates the different operation types.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/resource/resource-type.html" class="text-decoration-underline" target="_blank">Resource&nbsp;types</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                This example model demonstrates the different resource types.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/resource/resource-skills.html" class="text-decoration-underline" target="_blank">Resource&nbsp;skills</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                Resources can be assigned skills, which represent certain qualifications.<br>
         You can specify a required skill for an operation.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href={docroot}/examples/resource/resource-setup-matrices.html" class="text-decoration-underline" target="_blank">Setup&nbsp;matrices</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                Resources can require a setup time to change the configuration between different setups/configurations.
         This models the time required for cleaning, installation of new tooling, re-calibration, feeding new
         raw materials, etc.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/demand/demand-priorities.html" class="text-decoration-underline" target="_blank">Demand&nbsp;priorities</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                Demand priorities give you control over the allocation of constrained supply.
         Top priority orders will be the first to get the required material and capacity.
         Less prioritized orders are planned with the remaining availability and have
         a higher chance of being planned late or short.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/demand/demand-policies.html" class="text-decoration-underline" target="_blank">Demand&nbsp;policies</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                This model describes how to model demand policies like "ship all in full", "allow
         partial deliveries", "don't plan late shipments", etc.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/operation/operation-autofence.html" class="text-decoration-underline" target="_blank">Release&nbsp;fence</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                A release fence can be set to specify a frozen zone in the planning horizon in which
         the planning algorithm cannot propose any new manufacturing orders, purchase orders or distribution
         orders. The fence represents a period during which the plan is already being executed and can no
         longer be changed.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/buffer/transfer-batch.html" class="text-decoration-underline" target="_blank">Transfer&nbsp;batching</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                Transfer batching refers to operations that are planned with some overlap. The subsequent
         operation can already start when the previous one hasn't completely finished yet.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         
        <div class="trivision-row-card">
            <div style="flex: 0 0 100px; display:flex; flex-direction:column; align-items:center; justify-content:center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 18px; margin-right: 22px; gap:10px;">
                <span style="width:42px; height:42px; background:linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%); color:#fff; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; box-shadow:0 4px 12px rgba(45,0,77,0.28); transition:transform 0.2s ease;"><a href="{docroot}/examples/buffer/alternate-materials.html" class="text-decoration-underline" target="_blank">Alternate&nbsp;materials</a></h3>
            </div>
            <div style="flex: 1; color:#5C4670;">
                In many industries the bill of materials can contain alternate materials: the same product
         can be produced using different components.
            </div>
            <div style="flex: 0 0 220px; text-align: center; padding-left: 15px;">
                
            </div>
        </div>
        
         """.format(
                    **context
                ),
            }
        )
        index += 1

    # Feedback step - COMMENTED OUT
    # if index > 2:
    #     steps.append(
    #         {
    #             "index": index,
    #             "title": "Give us feedback",
    if False:  # Disabled: Give us feedback section
        steps.append(
            {
                "index": index,
                "title": "Give us feedback",
                "icon": None,
                "content": """
          
        <div class="trivision-row-card" style="align-items: stretch; padding: 1.5rem 2rem;">
            <div style="flex: 0 0 100px; display: flex; flex-direction: column; align-items: center; justify-content: center; border-right: 1px solid rgba(156,39,176,0.12); padding-right: 20px; margin-right: 24px; gap: 12px;">
                <div class="feedback-emoji" id="happy" style="width: 52px; height: 52px; border-radius: 50%; background: linear-gradient(145deg, #f0f0f0 0%, #e8e8e8 100%); display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.25s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <span class="fa fa-smile-o" style="font-size: 28px; color: #10B981;"></span>
                </div>
                <div class="feedback-emoji" id="average" style="width: 52px; height: 52px; border-radius: 50%; background: linear-gradient(145deg, #f0f0f0 0%, #e8e8e8 100%); display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.25s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <span class="fa fa-meh-o" style="font-size: 28px; color: #9CA3AF;"></span>
                </div>
                <div class="feedback-emoji" id="nothappy" style="width: 52px; height: 52px; border-radius: 50%; background: linear-gradient(145deg, #f0f0f0 0%, #e8e8e8 100%); display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.25s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <span class="fa fa-frown-o" style="font-size: 28px; color: #9CA3AF;"></span>
                </div>
            </div>
            <div style="flex: 1; display: flex; flex-direction: column;">
                <label style="font-family: 'Inter', -apple-system, sans-serif; font-weight: 600; color: #2D004D; margin-bottom: 0.75rem; font-size: 0.95rem;">Share your experience</label>
                <textarea id='textarea' class="form-control" style="width: 100%; border-radius: 14px; border: 2px solid rgba(156,39,176,0.12); box-shadow: 0 4px 12px rgba(123,45,142,0.04); padding: 1.25rem; color: #5C4670; font-family: 'Inter', -apple-system, sans-serif; resize: vertical; transition: all 0.3s ease; font-size: 0.9rem; line-height: 1.6;" rows="6"
                placeholder="We're eager to hear how well you found your way around. Choose a smiley and share your comments to help us improve!"></textarea>
                <div class="pt-3 text-end">
                    <button class="btn btn-primary" disabled id='submit' style="min-width: 180px; background: linear-gradient(135deg, #7B2D8E 0%, #A855F7 100%); border: none; border-radius: 25px; font-weight: 700; padding: 0.7rem 1.75rem; font-size: 0.85rem; letter-spacing: 0.3px; box-shadow: 0 4px 14px rgba(123,45,142,0.3); transition: all 0.25s ease; font-family: 'Inter', -apple-system, sans-serif;">Send us feedback</button>
                </div>
            </div>
        </div>
        <style>
            #textarea:focus {{
                box-shadow: 0 0 0 4px rgba(168,85,247,0.12);
                border-color: #A855F7;
                outline: none;
            }}
            .feedback-emoji:hover {{
                transform: scale(1.12);
                box-shadow: 0 4px 16px rgba(123,45,142,0.2);
            }}
            #happy.selected {{
                background: linear-gradient(145deg, #D1FAE5 0%, #A7F3D0 100%) !important;
                box-shadow: 0 4px 16px rgba(16,185,129,0.3);
            }}
            #average.selected {{
                background: linear-gradient(145deg, #FEF3C7 0%, #FDE68A 100%) !important;
                box-shadow: 0 4px 16px rgba(245,158,11,0.3);
            }}
            #nothappy.selected {{
                background: linear-gradient(145deg, #FEE2E2 0%, #FECACA 100%) !important;
                box-shadow: 0 4px 16px rgba(239,68,68,0.3);
            }}
            #submit:not(:disabled) {{
                pointer-events: auto;
            }}
            #submit:not(:disabled):hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(123,45,142,0.4);
                background: linear-gradient(135deg, #2D004D 0%, #7B2D8E 100%);
            }}
        </style>

      """.format(
                    **context
                ),
            }
        )
        script += (
            '''
       var $textarea = $('#textarea');
       var $submit = $('#submit');
       var $happy = $('#happy');
       var $average = $('#average');
       var $nothappy = $('#nothappy');
       var selectedFeeling = 'Average';

       // Set the onkeyup events
       $textarea.on('keyup', function() {
         $submit.prop('disabled', $.trim($textarea.val()) === '');
       });

       // Emoji selection handlers
       $happy.click( function() {
         $happy.addClass('selected');
         $average.removeClass('selected');
         $nothappy.removeClass('selected');
         $happy.find('.fa').css("color", "#10B981");
         $average.find('.fa').css("color", "#9CA3AF");
         $nothappy.find('.fa').css("color", "#9CA3AF");
         selectedFeeling = 'Happy';
         });
       $average.click( function() {
         $happy.removeClass('selected');
         $average.addClass('selected');
         $nothappy.removeClass('selected');
         $happy.find('.fa').css("color", "#9CA3AF");
         $average.find('.fa').css("color", "#F59E0B");
         $nothappy.find('.fa').css("color", "#9CA3AF");
         selectedFeeling = 'Average';
         });
       $nothappy.click( function() {
         $happy.removeClass('selected');
         $average.removeClass('selected');
         $nothappy.addClass('selected');
         $happy.find('.fa').css("color", "#9CA3AF");
         $average.find('.fa').css("color", "#9CA3AF");
         $nothappy.find('.fa').css("color", "#EF4444");
         selectedFeeling = 'Not happy';
         });

       $('#submit').click(function(e) {
           $.ajax({
               type: "POST",
               url: '/wizard/sendsurveymail/',
               data: {
                 'feeling': selectedFeeling,
                 'comments': $textarea.val()
                 },
               success: function() {
                 $textarea.val("Thank you for your comments!");
                 $submit.prop('disabled', true);
                 },
               error: function() {
                 $textarea.val(
                   $textarea.val()
                   + "\\n\\nOuch, our server couldn't send an email. Please email your feedback to info@frepple.com"
                   );
                 }
           });
       });

       $("input[data-parameter]").on('change', function(event) {
         var val = $(this).attr("data-parameter-value");
         if (typeof val === typeof undefined || val === false)
           val = $(this).val();
         $.ajax({
           type: 'POST',
           url: "'''
            + request.prefix
            + """/api/common/parameter/",
           data: {
             name: $(this).attr("data-parameter"),
             value: val
             }
           });
       });
       """
        )
        index += 1

    if steps:
        return {"steps": steps, "script": script, "mode": mode}
    else:
        return None


@staff_member_required
def WizardLoad(request, mode=None):
    db = request.database
    steps = getWizardSteps(request, mode)
    with_fcst_module = "freppledb.forecast" in settings.INSTALLED_APPS
    with_ip_module = "freppledb.inventoryplanning" in settings.INSTALLED_APPS
    if mode == "forecast" and with_fcst_module:
        title = _("Data loading wizard for forecasting")
    elif mode == "inventory" and with_ip_module:
        title = _("Data loading wizard for inventory planning")
    elif mode == "production":
        title = _("Data loading wizard for production planning")
    elif not mode:
        title = _("Get started - Data loading wizard")
    else:
        return HttpResponseServerError("Invalid wizard mode")
    context = {
        "prefix": "/" + request.prefix,
        "mode": mode,
        "wizard": steps,
        "with_fcst_module": with_fcst_module,
        "with_inventory_module": with_ip_module,
        "currentstep": int(request.GET.get("currentstep", 0)),
        "title": title,
        "bucketnames": Bucket.objects.order_by("-level").values_list("name", flat=True),
        "currency": getCurrency(),
    }
    if steps:
        context.update(
            {
                "noItem": not Item.objects.using(db).exists(),
                "noLocation": not Location.objects.using(db).exists(),
                "noCustomer": not Customer.objects.using(db).exists(),
                "noDemand": not Demand.objects.using(db).exists(),
                "noSupplier": not Supplier.objects.using(db).exists(),
                "noItemSupplier": not ItemSupplier.objects.using(db).exists(),
                "noItemDistribution": not ItemDistribution.objects.using(db).exists(),
                "noOperation": not Operation.objects.using(db).exists(),
                "noBuffer": not Buffer.objects.using(db).exists(),
                "noMO": not ManufacturingOrder.objects.using(db).exists(),
                "noMOproposed": not ManufacturingOrder.objects.filter(status="proposed")
                .using(db)
                .exists(),
                "noDO": not DistributionOrder.objects.using(db).exists(),
                "noPO": not PurchaseOrder.objects.using(db).exists(),
                "noResource": not Resource.objects.using(db).exists(),
                "noOperationMaterial": not OperationMaterial.objects.using(db).exists(),
                "noOperationResource": not OperationResource.objects.using(db).exists(),
            }
        )
        if with_fcst_module:
            context.update(
                {"noForecastPlan": not ForecastPlan.objects.using(db).exists()}
            )
    return render(request, "wizard/load.html", context=context)


class SendSurveyMail:
    @staticmethod
    @staff_member_required
    def action(request):
        # Dispatch to the correct method
        try:
            if request.method == "POST":
                sendEmail(
                    to="devops@frepple.com",
                    subject="Survey received from %s : %s"
                    % (request.build_absolute_uri()[:-23], request.POST.get("feeling")),
                    body=request.POST.get("comments"),
                )
                return HttpResponse("OK")
            else:
                return HttpResponseNotAllowed(["post"])
        except Exception:
            return HttpResponseServerError(
                "An error occurred when sending your comments"
            )


@staff_member_required
def CheckSupplyPath(request):
    item = request.GET.get("item", None)
    location = request.GET.get("location", None)
    if item and location:
        with connections[request.database].cursor() as cursor:
            cursor.execute(
                """
                with requesteditem as (
                  select name, lft, rght
                  from item where name = %s
                  )
                select distinct 'po'
                from itemsupplier
                inner join item
                  on itemsupplier.item_id = item.name
                inner join requesteditem
                  on requesteditem.lft between item.lft and item.rght
                where itemsupplier.location_id = %s or itemsupplier.location_id is null
                union all
                select distinct 'do'
                from itemdistribution
                inner join item
                  on itemdistribution.item_id = item.name
                inner join requesteditem
                  on requesteditem.lft between item.lft and item.rght
                where itemdistribution.location_id = %s or itemdistribution.location_id is null
                union all
                select distinct 'mo'
                from operation
                where operation.location_id = %s and operation.item_id = %s
                """,
                (item, location, location, location, item),
            )
            response = [rec[0] for rec in cursor.fetchall()]
    else:
        response = []
    return HttpResponse(
        content=json.dumps(response),
        content_type="application/json; charset=%s" % settings.DEFAULT_CHARSET,
    )


class QuickStartProduction(View):
    @method_decorator(staff_member_required())
    def get(self, request, *args, **kwargs):
        post = request.session.get("post", False)
        if post:
            del request.session["post"]
        return render(
            request,
            "wizard/quickstart_production.html",
            context={"title": _("Quickstart production planning"), "post": post},
        )

    @method_decorator(staff_member_required())
    def post(self, request, *args, **kwargs):
        try:
            db = request.database
            data = json.loads(
                request.body.decode(request.encoding or settings.DEFAULT_CHARSET)
            )
            post = {"salesorder": data["name"], "messages": []}

            items = 0
            locations = 0
            customers = 0
            suppliers = 0
            resources = 0
            itemsuppliers = 0
            itemdistributions = 0
            demands = 0
            operations = 0
            operationmaterials = 0
            operationresources = 0

            # Create item
            item, created = Item.objects.using(db).get_or_create(name=data["item"])
            if created:
                items += 1

            # Create location
            location, created = Location.objects.using(db).get_or_create(
                name=data["location"]
            )
            if created:
                locations += 1

            # Create customer
            customer, created = Customer.objects.using(db).get_or_create(
                name=data["customer"]
            )
            if created:
                customers += 1

            # Create demand
            created = Demand.objects.using(db).get_or_create(
                name=data["name"],
                defaults={
                    "item": item,
                    "location": location,
                    "customer": customer,
                    "due": parse(data["due"]),
                    "quantity": float(data["quantity"]),
                    "status": "open",
                },
            )
            if created:
                demands += 1
            for supply in data["supply"]:
                item, created = Item.objects.using(db).get_or_create(
                    name=supply["item"]
                )
                if created:
                    items += 1
                location, created = Location.objects.using(db).get_or_create(
                    name=supply["location"]
                )
                if created:
                    locations += 1
                if supply["type"] == "PO":
                    supplier, created = Supplier.objects.using(db).get_or_create(
                        name=supply["supplier"]
                    )
                    if created:
                        suppliers += 1
                    created = ItemSupplier.objects.using(db).get_or_create(
                        supplier=supplier,
                        item=item,
                        location=location,
                        defaults={
                            "leadtime": timedelta(days=float(supply["leadtime"]))
                        },
                    )[1]
                    if created:
                        itemsuppliers += 1
                elif supply["type"] == "DO":
                    origin, created = Location.objects.using(db).get_or_create(
                        name=supply["origin"]
                    )
                    if created:
                        locations += 1
                    created = ItemDistribution.objects.using(db).get_or_create(
                        item=item,
                        location=location,
                        origin=origin,
                        defaults={
                            "leadtime": timedelta(days=float(supply["leadtime"]))
                        },
                    )[1]
                    if created:
                        itemdistributions += 1
                elif supply["type"] == "MO":
                    operation, created = Operation.objects.using(db).get_or_create(
                        name=supply["operation"],
                        defaults={
                            "item": item,
                            "location": location,
                            "duration": parseDuration(supply["duration"]),
                            "duration_per": parseDuration(supply["durationper"]),
                            "type": "time_per",
                        },
                    )
                    if created:
                        operations += 1
                    if supply.get("resource", None):
                        resource, created = Resource.objects.using(db).get_or_create(
                            name=supply["resource"]
                        )
                        if created:
                            resources += 1
                        created = OperationResource.objects.using(db).get_or_create(
                            resource=resource,
                            operation=operation,
                            defaults={"quantity": 1},
                        )
                        if created:
                            operationresources += 1
                    consumedindex = 0
                    while True:
                        key = "consumeditem-%s" % consumedindex
                        if key not in supply:
                            break
                        if supply[key]:
                            item, created = Item.objects.using(db).get_or_create(
                                name=supply[key]
                            )
                            if created:
                                items += 1
                            try:
                                qty = -float(
                                    supply["consumedquantity-%s" % consumedindex]
                                )
                            except Exception:
                                qty = -1
                            created = OperationMaterial.objects.using(db).get_or_create(
                                item=item,
                                operation=operation,
                                defaults={"quantity": qty, "type": "start"},
                            )[1]
                            if created:
                                operationmaterials += 1
                        consumedindex += 1

            # Compile the messages
            if items > 0:
                post["messages"].append(
                    "Created %s new <a target='_blank' class='text-decoration-underline' href='%s/data/input/item/?noautofilter&sidx=lastmodified&amp;sord=desc'>item</a>"
                    % (items, request.prefix)
                )
            if locations > 0:
                post["messages"].append(
                    "Created %s new <a target='_blank' class='text-decoration-underline' href='%s/data/input/location/?noautofilter&sidx=lastmodified&amp;sord=desc'>location</a>"
                    % (locations, request.prefix)
                )
            if customers > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/customer/?noautofilter&sidx=lastmodified&amp;sord=desc'>customer</a>"
                    % (customers, request.prefix)
                )
            if demands > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/demand/?noautofilter&sidx=lastmodified&amp;sord=desc'>sales order</a>"
                    % (demands, request.prefix)
                )
            if suppliers > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/supplier/?noautofilter&sidx=lastmodified&amp;sord=desc'>supplier</a>"
                    % (suppliers, request.prefix)
                )
            if itemsuppliers > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/itemsupplier/?noautofilter&sidx=lastmodified&amp;sord=desc'>item supplier</a>"
                    % (itemsuppliers, request.prefix)
                )
            if itemdistributions > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/itemdistribution/?noautofilter&sidx=lastmodified&amp;sord=desc'>item distribution</a>"
                    % (itemdistributions, request.prefix)
                )
            if resources > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/resource/?noautofilter&sidx=lastmodified&amp;sord=desc'>resource</a>"
                    % (resources, request.prefix)
                )
            if operations > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/operation/?noautofilter&sidx=lastmodified&amp;sord=desc'>operation</a>"
                    % (operations, request.prefix)
                )
            if operationresources > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/operationresource/?noautofilter&sidx=lastmodified&amp;sord=desc'>operation resource</a>"
                    % (operationresources, request.prefix)
                )
            if operationmaterials > 0:
                post["messages"].append(
                    "Created %d new <a target='_blank' class='text-decoration-underline' href='%s/data/input/operationmaterial/?noautofilter&sidx=lastmodified&amp;sord=desc'>operation material</a>"
                    % (operationmaterials, request.prefix)
                )

            # Generate the plan
            management.call_command(
                "runplan",
                database=request.database,
                env="fcst,supply",
                constraint=13,
                background=True,
            )
            post["messages"].append(
                "<a target='_blank' class='text-decoration-underline' href='%s/execute/'>Generated the plan</a>"
                % request.prefix
            )

            # Leave feedback messages on the session
            request.session["post"] = post
            return HttpResponse(content="OK")

        except Exception as e:
            logger.error("Error creating supply path: %s" % e)
            post["messages"] = ["Error creating the supply path: %s" % e]
            request.session["post"] = post
            return HttpResponseServerError("Error creating supply path")


class FeatureDashboard(TemplateView):
    template_name = "wizard/features.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Explore features"
        return context


class QuickStartForecast(View):
    @method_decorator(staff_member_required())
    def get(self, request, *args, **kwargs):
        post = request.session.get("post", False)
        if post:
            del request.session["post"]
        return render(
            request,
            "wizard/quickstart_forecast.html",
            context={
                "title": _("Quickstart forecasting"),
                "post": post,
                "buckets": {
                    "day": _("days"),
                    "week": _("weeks"),
                    "month": _("months"),
                    "quarter": _("quarters"),
                }.get(
                    Parameter.getValue("forecast.calendar", request.database, None),
                    _("months"),
                ),
            },
        )

    @method_decorator(staff_member_required())
    def post(self, request, *args, **kwargs):
        post = {
            "item": request.POST.get("item", None),
            "location": request.POST.get("location", None),
            "customer": request.POST.get("customer", None),
            "messages": [],
        }
        history = request.POST.get("history", "").split()
        if (
            not post["item"]
            or not post["location"]
            or not post["customer"]
            or not history
        ):
            return HttpResponseNotAllowed("Missing information")

        # Create item
        item, created = Item.objects.using(request.database).get_or_create(
            name=post["item"]
        )
        if created:
            post["messages"].append(
                "Created a new <a target='_blank' class='text-decoration-underline' href='%s/data/input/item/?noautofilter&sidx=lastmodified&amp;sord=desc'>item</a>"
                % request.prefix
            )

        # Create location
        location, created = Location.objects.using(request.database).get_or_create(
            name=post["location"]
        )
        if created:
            post["messages"].append(
                "Created a new <a target='_blank' class='text-decoration-underline' href='%s/data/input/location/?noautofilter&sidx=lastmodified&amp;sord=desc'>location</a>"
                % request.prefix
            )

        # Create customer
        customer, created = Customer.objects.using(request.database).get_or_create(
            name=post["customer"]
        )
        if created:
            post["messages"].append(
                "Created a new <a target='_blank' class='text-decoration-underline' href='%s/data/input/customer/?noautofilter&sidx=lastmodified&amp;sord=desc'>customer</a>"
                % request.prefix
            )

        # Create demand
        created = False
        Demand.objects.using(request.database).filter(
            item=item, customer=customer, location=location, source="wizard"
        ).delete()
        cal = Parameter.getValue("forecast.calendar", request.database, "month")
        currentdate = getCurrentDate(request.database, lastplan=True).date()
        if not Bucket.objects.all().using(request.database).exists():
            management.call_command("createbuckets", database=request.database, task=-1)
        buckets = list(
            BucketDetail.objects.filter(bucket__name=cal, enddate__lte=currentdate)
            .order_by("-enddate")
            .only("name", "startdate", "enddate")[: len(history)]
        )
        idx = len(history)
        for qty in history:
            created = True
            idx -= 1
            (buckets[idx].enddate - buckets[idx].startdate) / 2
            Demand(
                name="History %s - %s - %s - %s"
                % (item.name, location.name, customer.name, buckets[idx].name),
                item=item,
                location=location,
                customer=customer,
                due=(
                    buckets[idx].startdate
                    + (buckets[idx].enddate - buckets[idx].startdate) / 2
                ).date(),
                quantity=float(qty),
                status="closed",
                source="wizard",
            ).save(using=request.database)
        if created:
            post["messages"].append(
                "Created %d closed <a target='_blank' class='text-decoration-underline' href='%s/data/input/demand/?noautofilter&sidx=lastmodified&amp;sord=desc'>sales orders</a>"
                % (len(history), request.prefix)
            )

        # Generate the plan
        management.call_command(
            "runplan",
            database=request.database,
            env="fcst,supply",
            constraint=13,
            background=True,
        )
        post["messages"].append(
            "<a target='_blank' class='text-decoration-underline' href='%s/execute/'>Generated the plan</a>"
            % request.prefix
        )

        # Don't return HTML, but a redirect after leaving info on the session
        request.session["post"] = post
        return HttpResponseRedirect("%s%s" % (request.prefix, request.path))
