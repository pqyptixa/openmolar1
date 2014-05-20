#! /usr/bin/env python
# -*- coding: utf-8 -*-

# ############################################################################ #
# #                                                                          # #
# # Copyright (c) 2009-2014 Neil Wallace <neil@openmolar.com>                # #
# #                                                                          # #
# # This file is part of OpenMolar.                                          # #
# #                                                                          # #
# # OpenMolar is free software: you can redistribute it and/or modify        # #
# # it under the terms of the GNU General Public License as published by     # #
# # the Free Software Foundation, either version 3 of the License, or        # #
# # (at your option) any later version.                                      # #
# #                                                                          # #
# # OpenMolar is distributed in the hope that it will be useful,             # #
# # but WITHOUT ANY WARRANTY; without even the implied warranty of           # #
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            # #
# # GNU General Public License for more details.                             # #
# #                                                                          # #
# # You should have received a copy of the GNU General Public License        # #
# # along with OpenMolar.  If not, see <http://www.gnu.org/licenses/>.       # #
# #                                                                          # #
# ############################################################################ #

'''
this module provides an html summary of the patient's details
'''

from __future__ import division

import datetime
import logging
import sys
from openmolar.settings import localsettings
from openmolar.dbtools import patient_class

LOGGER = logging.getLogger("openmolar")


def getAge(pt):
    '''
    display the patient's age in human readable form
    '''
    ageYears, months, isToday = pt.getAge()
    if isToday:
        return "<h5> %s TODAY!</h5>" % ageYears
    if ageYears > 18:
        return "(%syo)<hr />" % ageYears
    else:
        retarg = "<br />%s years" % ageYears
        if ageYears == 1:
            retarg = retarg.strip("s")
        retarg += " %s months" % months
        if months == 1:
            retarg = retarg.strip("s")
        return retarg + "<hr />"


def header(pt):
    retarg = '''<html>
<head><link rel="stylesheet" href="%s" type="text/css"></head>
<body><div align = "center">
<h4>Patient %d</h4>
<h3>%s %s %s</h3>
        ''' % (
        localsettings.stylesheet, pt.serialno, pt.title.title(),
        pt.fname.title(), pt.sname.title())

    retarg += '%s %s' % (localsettings.formatDate(pt.dob), getAge(pt))
    for line in (pt.addr1, pt.addr2, pt.addr3, pt.town, pt.county):
        if str(line) != '':
            retarg += "%s <br />" % line
    if pt.pcde == "":
        retarg += "<b>!UNKNOWN POSTCODE!</b>"
    else:
        retarg += "%s" % pt.pcde

    if not pt.status in ("Active", "", None):
        retarg += "<hr /><h1>%s</h1>" % pt.status

    return retarg


def details(pt, Saved=True):
    '''returns an html set showing pt name etc...'''

    try:
        retarg = header(pt) + '<hr />'
        if "N" in pt.cset:
            retarg += '''<img src="%s/nhs_scot.png" alt="NHS" />
            <br />''' % localsettings.resources_path

            if pt.exemption != "":
                retarg += " exemption=%s" % str(pt.exemption)
            else:
                retarg += "NOT EXEMPT"
            retarg += "<br />"
        elif "I" in pt.cset:
            retarg += '''<img src="%s/hdp_small.png" alt="HDP" />
            <br />''' % localsettings.resources_path

        elif "P" in pt.cset:
            retarg += '''<img src="%s/private.png" alt="PRIVATE" />
            <br />''' % localsettings.resources_path

        else:
            retarg += 'UNKNOWN COURSETYPE = %s <br />' % str(pt.cset)

        retarg += "%s<br />" % pt.fee_table.briefName
        try:
            retarg += 'dentist      = %s' % localsettings.ops[pt.dnt1]
            if pt.dnt2 != 0 and pt.dnt1 != pt.dnt2:
                retarg += '/%s' % localsettings.ops[pt.dnt2]
        except KeyError as e:
            retarg += '<h4>Please Set a Dentist for this patient!</h4><hr />'
        if pt.memo != '':
            retarg += '<h4>Memo</h4>%s<hr />' % pt.memo

        tx_dates = [
            (_("Treatment"), pt.last_treatment_date),
            (_("IO xrays"), pt.pd9),
            (_("Panoral"), pt.pd8),
            (_("Scaling"), pt.pd10)
        ]

        letype, le_date = "", datetime.date(1, 1, 1)
        for i, date_ in enumerate((pt.pd5, pt.pd6, pt.pd7)):
            if date_ and date_ > le_date:
                le_date = date_
                letype = ("(CE)", "(ECE)", "(FCA)")[i]
        if le_date == datetime.date(1, 1, 1):
            le_date = None
        if letype != "":
            tx_dates.append(('%s %s' % (_("Exam"), letype), le_date))

        retarg += '<h4>%s</h4><table width="100%%" border="1">' % _("History")
        for i, (att, val) in enumerate(tx_dates):

            retarg += '''<tr><td align="center">%s</td>
            <td align="center">%s%s%s</td></tr>''' % (
                att,
                "<b>" if i in (0, 4) else "",
                localsettings.formatDate(val),
                "</b>" if i in (0, 4) else "")

        retarg += "</table>"

        retarg += "<h4>%s</h4>%s" % (
            _("Recall"),
            localsettings.formatDate(pt.recd) if pt.recall_active else _(
                "DO NOT RECALL")
        )

        if not Saved:
            alert = "<br />NOT SAVED"
        else:
            alert = ""
        if pt.fees > 0:
            amount = localsettings.formatMoney(pt.fees)
            retarg += '<hr /><h3 class="debt">Account = %s %s</h3>' % (
                amount, alert)
        if pt.fees < 0:
            amount = localsettings.formatMoney(-pt.fees)
            retarg += '<hr /><h3>%s in credit %s</h3>' % (amount, alert)

        if pt.underTreatment:
            retarg += '<hr /><h2 class="ut_label">UNDER TREATMENT</h2><hr />'

        return '''%s\n</div></body></html>''' % retarg
    except Exception as exc:
        LOGGER.exception("error in patientDetails.details")
        return "error displaying details, sorry <br />%s" % exc

if __name__ == '__main__':
    localsettings.initiate()
    localsettings.loadFeeTables()
    try:
        serialno = int(sys.argv[len(sys.argv) - 1])
    except:
        serialno = 4792
    if '-v' in sys.argv:
        verbose = True
    else:
        verbose = False
    print details(patient_class.patient(serialno))
