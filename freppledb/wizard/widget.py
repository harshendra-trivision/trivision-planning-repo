#
# Copyright (C) 2023 by frePPLe bv
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

from django.middleware.csrf import get_token
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str

from freppledb.common.dashboard import Dashboard, Widget


class WizardWidget(Widget):
    name = "wizard"
    title = _("Loading your first data")
    asynchronous = False
    size = "xl"

    def render(self, request=None):
        from freppledb.common.middleware import _thread_locals

        return """
        <style>
            .trivision-wizard-column {
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                padding: 1rem;
                height: 100%%;
            }
            .trivision-icon-container {
                position: relative;
                display: inline-block;
                margin-bottom: 1.5rem;
            }
            .trivision-icon-circle {
                width: 70px;
                height: 70px;
                border-radius: 50%%;
                border: 2px solid #E1BEE7;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.8rem;
                color: #7B2D8E;
                background: #FFFFFF;
                transition: all 0.3s ease;
            }
            .trivision-icon-letter {
                position: absolute;
                top: -5px;
                left: -5px;
                width: 22px;
                height: 22px;
                border-radius: 50%%;
                background: #A855F7;
                color: #FFFFFF;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.75rem;
                font-weight: bold;
                box-shadow: 0 2px 4px rgba(168,85,247,0.4);
                font-family: 'Inter', sans-serif;
            }
            .trivision-wizard-column:hover .trivision-icon-circle {
                transform: scale(1.05);
                border-color: #A855F7;
                box-shadow: 0 4px 12px rgba(168,85,247,0.2);
            }
            .trivision-btn-primary {
                background: #A855F7 !important;
                color: #FFFFFF !important;
                border: none !important;
                border-radius: 20px !important;
                font-weight: 800 !important;
                padding: 0.5rem 1.5rem !important;
                transition: all 0.25s ease !important;
                font-family: 'Inter', sans-serif;
            }
            .trivision-btn-primary:hover, .trivision-btn-dropdown:hover {
                background: #7B2D8E !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(123,45,142,0.2) !important;
            }
            .trivision-dropdown-menu {
                background-color: #FFFFFF !important;
                border-radius: 10px !important;
                box-shadow: 0 8px 30px rgba(123,45,142,0.12) !important;
                border: 1px solid rgba(156,39,176,0.15) !important;
                padding: 0.5rem !important;
                min-width: 200px;
            }
            .trivision-dropdown-item {
                color: #7B2D8E !important;
                background: transparent !important;
                border: none !important;
                text-align: center !important;
                font-weight: 600 !important;
                border-radius: 6px !important;
                padding: 0.5rem 1rem !important;
                transition: all 0.2s ease !important;
                margin-bottom: 0.25rem !important;
                box-shadow: none !important;
                font-family: 'Inter', sans-serif;
            }
            .trivision-dropdown-item:hover {
                color: #A855F7 !important;
                background: rgba(168,85,247,0.15) !important;
                transform: translateY(-1px) !important;
            }
            .trivision-row-card {
                display: flex;
                align-items: center;
                background: #FFFFFF;
                border-radius: 12px;
                padding: 1rem 1.5rem;
                margin-bottom: 1rem;
                box-shadow: 0 4px 12px rgba(123,45,142,0.05);
                border: 1px solid rgba(156,39,176,0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .trivision-row-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(123,45,142,0.1);
                border-color: rgba(156,39,176,0.2);
            }
        </style>
        <div class="row pt-4 pb-2">
            <div class="col-auto justify-content-center d-flex w-100">
                <h1 style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 1.25rem; color: #1A0033;">Three ways to get started quickly</h1>
            </div>
        </div>
        <div class="row pb-4 gy-4 justify-content-center" id="wizard">

            <div class="col-md-4">
                <div class="trivision-wizard-column">
                    <div class="trivision-icon-container">
                        <div class="trivision-icon-circle"><i class="fa fa-hand-pointer-o"></i></div>
                        <div class="trivision-icon-letter">A</div>
                    </div>
                    <h2 style="font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 800; color: #1A0033; margin-bottom: 0.5rem;">Start with one item</h2>
                    <p style="font-family: 'Inter', sans-serif; color:#9B8AAE; font-size: 0.8rem; margin-bottom: 1.5rem;">Begin exploring with a single product</p>
                    <div class="dropdown-center mt-auto">
                        <button class="btn btn-primary trivision-btn-primary" type="button" data-bs-toggle="dropdown" aria-expanded="false" style="min-width: 140px; font-size: 0.75rem; letter-spacing: 0.5px;">
                            QUICKSTART <i class="fa fa-angle-down ms-1" style="font-size: 0.9rem;"></i>
                        </button>
                        <ul class="dropdown-menu trivision-dropdown-menu">
                            <li><a href="%s/wizard/quickstart/forecast/" class="btn btn-primary w-100 trivision-dropdown-item">FORECAST</a></li>
                            <li><a href="%s/wizard/quickstart/production/" class="btn btn-primary w-100 trivision-dropdown-item">PRODUCTION</a></li>
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
                    <h2 style="font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 800; color: #1A0033; margin-bottom: 0.5rem;">Upload more data</h2>
                    <p style="font-family: 'Inter', sans-serif; color:#9B8AAE; font-size: 0.8rem; margin-bottom: 1.5rem;">Import your datasets via CSV or Excel</p>
                    <div class="dropdown-center mt-auto">
                        <button class="btn btn-primary trivision-btn-primary" type="button" data-bs-toggle="dropdown" aria-expanded="false" style="min-width: 140px; font-size: 0.75rem; letter-spacing: 0.5px;">
                            UPLOAD <i class="fa fa-angle-down ms-1" style="font-size: 0.9rem;"></i>
                        </button>
                        <ul class="dropdown-menu trivision-dropdown-menu">
                            <li><a class="btn btn-primary w-100 trivision-dropdown-item" href="%s/wizard/load/forecast/">FORECAST</a></li>
                            <li><a class="btn btn-primary w-100 trivision-dropdown-item" href="%s/wizard/load/production/">PRODUCTION</a></li>
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
                    <h2 style="font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 800; color: #1A0033; margin-bottom: 0.5rem;">Import from Odoo</h2>
                    <p style="font-family: 'Inter', sans-serif; color:#9B8AAE; font-size: 0.8rem; margin-bottom: 1.5rem;">Sync directly with your ERP system</p>
                    <div class="dropdown-center mt-auto">
                        <a href="%s/data/common/parameter/?noautofilter&name__contains=odoo" class="btn btn-primary trivision-btn-primary" style="min-width: 140px; font-size: 0.75rem; letter-spacing: 0.5px; display: inline-flex; justify-content: center; align-items: center;">
                            CONNECT
                        </a>
                    </div>
                </div>
            </div>

        </div>""" % (
            _thread_locals.request.prefix,
            _thread_locals.request.prefix,
            _thread_locals.request.prefix,
            _thread_locals.request.prefix,
            _thread_locals.request.prefix,
        )


Dashboard.register(WizardWidget)
