#
# Copyright (C) 2020 by frePPLe bv
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

from urllib.parse import urlencode

from django.contrib.admin.utils import quote
from django.db import connections
from django.db.models import F
from django.http import HttpResponse
from django.utils.encoding import force_str
from django.utils.html import escape
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from freppledb.common.dashboard import Dashboard, Widget
from freppledb.common.models import UserPreference
from freppledb.common.report import getCurrency
from freppledb.input.models import Item


@Dashboard.register
class AnalysisDemandProblems(Widget):
    name = "analysis_demand_problems"
    title = _("analyze late demands")
    tooltip = _("Spot the top items with many late demands")
    permissions = (("view_demand_report", "Can view demand report"),)
    asynchronous = True
    url = "/demand/?noautofilter&sidx=latedemandvalue%20desc%2C%20latedemandquantity%20desc%2C%20latedemandcount&sord=desc"
    exporturl = True
    size = "lg"
    limit = 20
    orderby = "latedemandvalue"

    def args(self):
        return "?%s" % urlencode({"limit": self.limit, "orderby": self.orderby})

    @classmethod
    def render(cls, request=None):
        limit = int(request.GET.get("limit", cls.limit))
        orderby = request.GET.get("orderby", cls.orderby)
        currency = getCurrency()
        result = [
            '<div class="table-responsive"><table class="table table-sm table-hover">',
            '<thead><tr><th class="alignleft">%s</th><th class="text-center">%s</th>'
            '<th class="text-center">%s</th><th class="text-center">%s</th></tr></thead>'
            % (
                capfirst(force_str(_("item"))),
                capfirst(force_str(_("value of late demands"))),
                capfirst(force_str(_("quantity of late demands"))),
                capfirst(force_str(_("number of late demands"))),
            ),
        ]
        if orderby == "latedemandcount":
            topitems = (
                Item.objects.all()
                .using(request.database)
                .order_by("-latedemandcount", "latedemandvalue", "-latedemandquantity")
                .filter(rght=F("lft") + 1, latedemandcount__gt=0)
                .only(
                    "name", "latedemandcount", "latedemandquantity", "latedemandvalue"
                )[:limit]
            )
        elif orderby == "latedemandquantity":
            topitems = (
                Item.objects.all()
                .using(request.database)
                .order_by("-latedemandquantity", "latedemandvalue", "-latedemandcount")
                .filter(rght=F("lft") + 1, latedemandcount__gt=0)
                .only(
                    "name", "latedemandcount", "latedemandquantity", "latedemandvalue"
                )[:limit]
            )
        else:
            topitems = (
                Item.objects.all()
                .using(request.database)
                .order_by("-latedemandvalue", "-latedemandquantity", "-latedemandcount")
                .filter(rght=F("lft") + 1, latedemandcount__gt=0)
                .only(
                    "name", "latedemandcount", "latedemandquantity", "latedemandvalue"
                )[:limit]
            )
        alt = False
        for rec in topitems:
            result.append(
                '<tr%s><td class="text-decoration-underline"><a href="%s/buffer/item/%s/">%s</a></td>'
                '<td class="text-center">%s%s%s</td><td class="text-center">%s</td>'
                '<td class="text-center">%s</td></tr>'
                % (
                    alt and ' class="altRow"' or "",
                    request.prefix,
                    quote(rec.name),
                    escape(rec.name),
                    currency[0],
                    int(rec.latedemandvalue),
                    currency[1],
                    int(rec.latedemandquantity),
                    rec.latedemandcount,
                )
            )
            alt = not alt
        result.append("</table></div>")
        return HttpResponse("\n".join(result))


class DeliveryPerformanceWidget(Widget):
    name = "delivery_performance"
    title = _("delivery performance")
    tooltip = _(
        "Shows the percentage of demands that are planned to be shipped completely on time"
    )
    permissions = (("view_demand", "Can view sales order"),)
    asynchronous = True
    size = "sm"

    javascript = """
        var chart_type = "count";
        var include_fcst = false;

        $("#deliveryPerformanceDropdown a").on("click", function(event) {
            event.preventDefault();
            var selection = $(this).text().toLowerCase();
            $("#deliveryPerformanceChoice span").text(selection);
            include_fcst = (selection == "orders") ? false: true;
            draw();
        });

        function draw() {
            var delivery_data = include_fcst ? [
                { category: "ontime_so", label: "on-time orders", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradOntime)", color: "#5C197B" },
                { category: "ontime_fcst", label: "on-time forecast", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradOntimeFcst)", color: "#A855F7" },
                { category: "late_so", label: "late orders", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradLate)", color: "#F59E0B" },
                { category: "late_fcst", label: "late forecast", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradLateFcst)", color: "#FCD34D" },
                { category: "unplanned_so", label: "unplanned orders", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradUnplanned)", color: "#DC2626" },
                { category: "unplanned_fcst", label: "unplanned forecast", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradUnplannedFcst)", color: "#FCA5A5" }
            ] : [
                { category: "ontime_so", label: "on-time orders", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradOntime)", color: "#5C197B" },
                { category: "late_so", label: "late orders", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradLate)", color: "#F59E0B" },
                { category: "unplanned_so", label: "unplanned orders", value: 0, count: 0, quantity: 0, cost: 0, gradient: "url(#gradUnplanned)", color: "#DC2626" }
            ] ;

            // Collect data
            $("#deliveryPerformanceData td").each(function(i, e) {
                var el = $(e);
                var category = el.closest("tr").attr("data-category");
                var metric = el.attr("data-metric");
                for (var j = 0; j < delivery_data.length; j++) {
                    if (delivery_data[j].category == category) {
                        if (metric == chart_type) delivery_data[j].value = Number(el.text());
                        if (metric == "count") delivery_data[j].count = Number(el.text());
                        if (metric == "quantity") delivery_data[j].quantity = Number(el.text());
                        if (metric == "cost") delivery_data[j].cost = Number(el.text());
                    }
                }
            });

            // Remove empty cells
            delivery_data = delivery_data.filter(function(row) {return row.value > 0;});
            var total = d3.sum(delivery_data, function(d) { return d.value; });

            // Clear previous chart
            d3.select('#deliveryPerformanceChart').selectAll("*").remove();

            // Donut chart with gradients
            var width = 350;
            var height = 350;
            var radius = Math.min(width, height) / 2;
            var innerRadius = radius * 0.5;
            var svg = d3.select('#deliveryPerformanceChart')
                .attr('width', width)
                .attr('height', height);

            // Define gradients
            var defs = svg.append("defs");

            // On-time gradient (deep purple)
            var g1 = defs.append("linearGradient").attr("id", "gradOntime")
                .attr("x1", "0%").attr("y1", "0%").attr("x2", "100%").attr("y2", "100%");
            g1.append("stop").attr("offset", "0%").attr("stop-color", "#7B2D8E");
            g1.append("stop").attr("offset", "100%").attr("stop-color", "#5C197B");

            // On-time forecast gradient (light purple)
            var g2 = defs.append("linearGradient").attr("id", "gradOntimeFcst")
                .attr("x1", "0%").attr("y1", "0%").attr("x2", "100%").attr("y2", "100%");
            g2.append("stop").attr("offset", "0%").attr("stop-color", "#C084FC");
            g2.append("stop").attr("offset", "100%").attr("stop-color", "#A855F7");

            // Late gradient (amber)
            var g3 = defs.append("linearGradient").attr("id", "gradLate")
                .attr("x1", "0%").attr("y1", "0%").attr("x2", "100%").attr("y2", "100%");
            g3.append("stop").attr("offset", "0%").attr("stop-color", "#FBBF24");
            g3.append("stop").attr("offset", "100%").attr("stop-color", "#F59E0B");

            // Late forecast gradient (light amber)
            var g4 = defs.append("linearGradient").attr("id", "gradLateFcst")
                .attr("x1", "0%").attr("y1", "0%").attr("x2", "100%").attr("y2", "100%");
            g4.append("stop").attr("offset", "0%").attr("stop-color", "#FDE68A");
            g4.append("stop").attr("offset", "100%").attr("stop-color", "#FCD34D");

            // Unplanned gradient (red)
            var g5 = defs.append("linearGradient").attr("id", "gradUnplanned")
                .attr("x1", "0%").attr("y1", "0%").attr("x2", "100%").attr("y2", "100%");
            g5.append("stop").attr("offset", "0%").attr("stop-color", "#EF4444");
            g5.append("stop").attr("offset", "100%").attr("stop-color", "#DC2626");

            // Unplanned forecast gradient (light red)
            var g6 = defs.append("linearGradient").attr("id", "gradUnplannedFcst")
                .attr("x1", "0%").attr("y1", "0%").attr("x2", "100%").attr("y2", "100%");
            g6.append("stop").attr("offset", "0%").attr("stop-color", "#FECACA");
            g6.append("stop").attr("offset", "100%").attr("stop-color", "#FCA5A5");

            var chartGroup = svg.append('g')
                .attr('transform', "translate(" + (width / 2) + ", " + (height / 2) + ")");

            var pie = d3.layout.pie()
                .sort(null)
                .startAngle(Math.PI / 2)
                .endAngle(Math.PI * 2.5)
                .value(function(d) { return d.value; });

            var arc = d3.svg.arc()
                .innerRadius(innerRadius)
                .outerRadius(radius - 10);

            var slices = chartGroup.selectAll('path')
                .data(pie(delivery_data))
                .enter()
                .append('path')
                .attr('d', arc)
                .attr('fill', function(d) { return d.data.gradient; })
                .attr('stroke', 'white')
                .style('stroke-width', '2px')
                .on("mouseover", function(d) {
                    graph.showTooltip(
                        '<span class="text-strong">' + d.data.label + "</span>"
                        + "<br>count: "
                        + d.data.count.toLocaleString('en-US', {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 2
                          })
                        + "<br>quantity: "
                        + d.data.quantity.toLocaleString('en-US', {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 2
                          })
                        + (d.data.cost ? "<br>cost: "
                        + d.data.cost.toLocaleString('en-US', {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 2
                          })
                        + " " + currency[1] : "")
                        );
                    $("#tooltip").css('background-color','#1F2937').css('color','white').css('border-radius','8px').css('padding','10px');
                })
                .on("mousemove", graph.moveTooltip)
                .on("mouseout", graph.hideTooltip);

            // Center text showing total
            chartGroup.append('text')
                .attr('text-anchor', 'middle')
                .attr('dy', '-0.2em')
                .style('font-size', '24px')
                .style('font-weight', '700')
                .style('fill', '#5C197B')
                .text(total.toLocaleString());
            chartGroup.append('text')
                .attr('text-anchor', 'middle')
                .attr('dy', '1.2em')
                .style('font-size', '12px')
                .style('fill', '#6B7280')
                .text('total');

            // Labels
            chartGroup.selectAll('text.label')
                .data(pie(delivery_data))
                .enter()
                .append('text')
                .attr('class', 'label')
                .attr('transform', function(d) {
                    var center = arc.centroid(d);
                    var rotation = ((d.startAngle + d.endAngle) / 2 * 180 / Math.PI) - 90;
                    if (rotation > 90 && rotation <= 270) rotation += 180;
                    return "translate(" + (center[0] * 1.9) + "," + (center[1] * 1.9) + ") rotate(" + rotation + ")";
                })
                .style('text-anchor', function(d){
                    var rotation = ((d.startAngle + d.endAngle) / 2 * 180 / Math.PI) - 90;
                    return (rotation <= 90 || rotation > 270) ? 'end' : 'start';
                })
                .attr('dy', '.35em')
                .style('font-size', '11px')
                .style('font-weight', '600')
                .style('fill', function(d) { return d.data.color; })
                .text(function(d) {
                    var perc = ((d.data.value / total) * 100).toFixed(0);
                    return d.data.label + " " + perc + "%";
                });
        }
        draw();
        """

    @classmethod
    def render(cls, request):
        result = [
            '<div class="d-flex justify-content-center align-items-center h-100 position-relative">',
            '<svg id="deliveryPerformanceChart"></svg>'
            '<div class="dropdown position-absolute top-0 end-0 m-3">',
            '<button id="deliveryPerformanceChoice" class="form-select form-select-sm d-inline-block w-auto text-capitalize" type="button" data-bs-toggle="dropdown" aria-expanded="false">',
            "<span>orders</span>",
            "</button>",
            '<ul id="deliveryPerformanceDropdown" class="dropdown-menu w-auto" style="min-width: unset" aria-labelledby="fcst_selectButton">',
            '<li><a class="dropdown-item text-capitalize">orders</a></li>',
            '<li><a class="dropdown-item text-capitalize">orders and forecast</a></li>',
            "</ul>",
            "</div>",
            '<div id="deliveryPerformanceData"class="d-none"><table>',
        ]
        try:
            for cat, kv in (
                UserPreference.objects.using(request.database)
                .get(property="widget.deliveryperformance")
                .value.items()
            ):
                result.append(f'<tr data-category="{cat}">')
                for k, v in kv.items():
                    result.append(f'<td data-metric="{k}">{v}</td>')
                result.append("</tr>")
        except UserPreference.DoesNotExist:
            pass
        result.append("</table></div></div>")
        return HttpResponse("\n".join(result))


Dashboard.register(DeliveryPerformanceWidget)
