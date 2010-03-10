# -*- coding: utf-8 -*-
# Copyright (c) 2009 Neil Wallace. All rights reserved.
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# See the GNU General Public License for more details.

'''
this module contains functions which were originally part of the maingui.py
script, concerning fees, accounts and graphical feescale display.
'''

from __future__ import division

from PyQt4 import QtGui, QtCore
import os
import subprocess

from openmolar.dbtools import feesTable, accounts, patient_class, cashbook, \
patient_write_changes
from openmolar.settings import localsettings
from openmolar.qt4gui.fees import fee_table_model
from openmolar.qt4gui.fees import edit_feeitem_dialog

from openmolar.qt4gui.printing import om_printing
from openmolar.qt4gui.dialogs import paymentwidget
from openmolar.qt4gui.compiled_uis import Ui_chooseDocument
from openmolar.qt4gui.compiled_uis import Ui_raiseCharge

def raiseACharge(om_gui):
    '''
    this is called by the "raise a charge" button on the
    clinical summary page
    '''
    ##TODO
    ###obsolete code
    print "WARNING - obsolete code executed fees_module.raiseACharge"
    if om_gui.pt.serialno == 0:
        om_gui.advise("No patient Selected", 1)
        return
    Dialog = QtGui.QDialog(om_gui)
    dl = Ui_raiseCharge.Ui_Dialog()
    dl.setupUi(Dialog)
    if Dialog.exec_():
        fee = dl.doubleSpinBox.value()
        if om_gui.pt.cset[:1] == "N":
            om_gui.pt.money0 += int(fee*100)
        else:
            om_gui.pt.money1 += int(fee*100)
        updateFees(om_gui)
        om_gui.pt.addHiddenNote("treatment", " %s"%
        str(dl.lineEdit.text().toAscii()))

        om_gui.pt.addHiddenNote("fee", "%.02f"% fee)
        om_gui.updateHiddenNotesLabel()
            
    ################################################
    
def applyFeeNow(om_gui, arg, cset=None):
    '''
    updates the patients outstanding money
    '''
    om_gui.pt.applyFee(arg, cset)
    updateFees(om_gui)

def updateFees(om_gui):
    '''
    recalc money and
    update the details down the left hand side
    '''
    if om_gui.pt.serialno != 0:
        om_gui.pt.updateFees()
        om_gui.updateDetails()
        
def getFeesFromEst(om_gui, tooth, treat):
    '''
    iterate through the ests... find this item
    '''
    tooth = tooth.rstrip("pl")
    retarg = (0,0)
    for est in om_gui.pt.estimates:
        if est.type == treat.strip(" "):
            retarg = (est.fee, est.ptfee)
            break
    return retarg

def takePayment(om_gui):
    '''
    raise a dialog, and take some money
    '''
    if om_gui.pt.serialno == 0:
        om_gui.advise("No patient Selected <br />Monies will be "+ \
        "allocated to Other Payments, and no receipt offered", 1)
    dl = paymentwidget.paymentWidget(om_gui)
    dl.setDefaultAmount(om_gui.pt.fees)
    if dl.exec_():
        if om_gui.pt.serialno == 0:
            paymentPt = patient_class.patient(18222)
        else:
            paymentPt = om_gui.pt
        cash = dl.cash_lineEdit.text()
        cheque = dl.cheque_lineEdit.text()
        debit = dl.debitCard_lineEdit.text()
        credit = dl.creditCard_lineEdit.text()
        sundries = dl.sundries_lineEdit.text()
        hdp = dl.annualHDP_lineEdit.text()
        other = dl.misc_lineEdit.text()
        total = dl.total_doubleSpinBox.value()
        name = "%s %s"% (paymentPt.sname, paymentPt.fname[:1])
        if paymentPt.dnt2 != 0:
            dent = paymentPt.dnt2
        else:
            dent = paymentPt.dnt1

        if cashbook.paymenttaken(paymentPt.serialno, name, dent,
        paymentPt.cset, cash, cheque, debit, credit, sundries, hdp, other):
            paymentPt.addHiddenNote("payment", 
            " treatment %.02f sundries %.02f"% (dl.paymentsForTreatment, 
            dl.otherPayments))

            if om_gui.pt.serialno != 0:
                om_printing.printReceipt(om_gui,{
                "Professional Services" : dl.paymentsForTreatment * 100, 
                "Other Items" : dl.otherPayments * 100})

                #-- always refer to money in terms of pence

                if om_gui.pt.cset[:1] == "N":
                    om_gui.pt.money2 += int(dl.paymentsForTreatment*100)
                else:
                    om_gui.pt.money3 += int(dl.paymentsForTreatment*100)
                om_gui.pt.updateFees()

            patient_write_changes.toNotes(paymentPt.serialno,
                                          paymentPt.HIDDENNOTES)

            if patient_write_changes.discreet_changes(paymentPt,
            ("money2", "money3")) and om_gui.pt.serialno != 0:

                om_gui.pt_dbstate.money2 = om_gui.pt.money2
                om_gui.pt_dbstate.money3 = om_gui.pt.money3

            paymentPt.clearHiddenNotes()
            om_gui.updateDetails()
            om_gui.updateHiddenNotesLabel()
            
        else:
            om_gui.advise("error applying payment.... sorry!<br />"\
            +"Please write this down and tell Neil what happened", 2)

def loadFeesTable(om_gui):
    '''
    loads the fee table
    '''
    om_gui.feestableLoaded = True
    
    tableKeys = localsettings.FEETABLES.tables.keys()
    tableKeys.sort()
    for key in tableKeys:
        table = localsettings.FEETABLES.tables[key]
        model = fee_table_model.treeModel(table)
        om_gui.fee_models.append(model)  
        om_gui.ui.chooseFeescale_comboBox.addItem(table.briefName)
    
    n = len(om_gui.fee_models)
    text = "%d "%n + _("Fee Scales Available")
    om_gui.ui.feescales_available_label.setText(text) 
    
    print "loaded feesTable, %d fee models in use"% n
    
def table_clicked(om_gui, index):
    '''
    user has clicked an item on the feetable.
    show the user some options (depending on whether they have a patient 
    loaded for edit, or are in feetable adjust mode etc....
    '''
    fee_item = om_gui.ui.feeScales_treeView.model().data(index, 
    QtCore.Qt.UserRole)
    
    if not fee_item: 
        # this will be the case if a header item was clicked
        return
    
    def edit_fee_item():
        '''
        user wishes to alter a fee item
        '''
        
        Dialog = QtGui.QDialog()
        dl = edit_feeitem_dialog.editFee(fee_item, Dialog)
    
        print dl.getInput()
        
        
    def apply(arg):
        '''
        apply the result of the QMenu generated when feetable is clicked
        '''
        if arg.text() == _("Adjust / edit this Item"):
            edit_fee_item()
        elif arg.text().startsWith(_("Add to tx plan")):
                om_gui.feeScaleTreatAdd(fee_item)
        else:
            om_gui.advise(arg.text() + " not yet available", 1)
    
    menu = QtGui.QMenu(om_gui)
    ptno = om_gui.pt.serialno 
    if ptno != 0:
        menu.addAction(_("Add to tx plan of patient")+" %d"% ptno)
        menu.addSeparator()                
    menu.addAction(_("Adjust / edit this Item"))
    menu.addSeparator()
    menu.addAction(_("Delete Item"))
    menu.addAction(_("Insert New Item"))

    choice = menu.exec_(om_gui.cursor().pos())
    if choice:
        apply(choice)

def feeSearch(om_gui):
    '''
    user has finished editing the
    feesearchLineEdit - time to refill the searchList
    '''
    def ensureVisible(index):
        ''' expand all parents of a found leaf'''
        parentIndex = model.parent(index)
        om_gui.ui.feeScales_treeView.setExpanded(parentIndex, True)
        if parentIndex.internalPointer() != None:
            ensureVisible(parentIndex)        
        
    search_phrase = om_gui.ui.feeSearch_lineEdit.text()
    model = om_gui.fee_models[
    om_gui.ui.chooseFeescale_comboBox.currentIndex()]

    columns = []
    if om_gui.ui.feesSearch_usercodes_checkBox.isChecked():
        columns.append(1)
    if om_gui.ui.feesSearch_descriptions_checkBox.isChecked():
        columns.append(2)
        columns.append(4)
    if columns:
        om_gui.wait(True)
        if model.search(search_phrase, columns):
            om_gui.ui.feeScales_treeView.collapseAll()        
            indexes = model.foundItems
            
            om_gui.ui.feesearch_results_label.setText(
            "%d %s %s"%(len(indexes), _("Items containing"), search_phrase))
            for index in indexes:
                ensureVisible(index)
            om_gui.wait(False)
        else:
            om_gui.wait(False)
            message = _("phrase not found in feetable")
            if 1 in columns and 4 in columns:
                message += " " + _("usercodes or descriptions")            
            elif 1 in columns:
                message += " " + _("usercodes")
            elif 4 in columns:
                message += " " + _("descriptions")
            om_gui.advise(message, 1)
        
    else:
        om_gui.advise(_("nothing to search")+ "<br />" +
        _("please select usercodes and/or descriptions then search again"), 1)
        
def nhsRegsPDF(om_gui):
    '''
    I have some stored PDF documents
    the user wants to see these
    '''
    Dialog = QtGui.QDialog(om_gui)
    dl = Ui_chooseDocument.Ui_Dialog()
    dl.setupUi(Dialog)
    if Dialog.exec_():
        if dl.tabWidget.currentIndex()==0:
            if dl.info_radioButton.isChecked():
                doc = os.path.join(localsettings.wkdir, 'resources', 
                "Dental_Information_Guide_2008_v4.pdf")
            else:
                doc = os.path.join(localsettings.wkdir, 'resources', 
                "scotNHSremuneration08.pdf")
        else:
            if dl.info2009_radioButton.isChecked():
                doc = os.path.join(localsettings.wkdir, 'resources', 
                "Dental_Information_Guide_2009.pdf")
            else:
                doc = os.path.join(localsettings.wkdir, 'resources', 
                "scotNHSremuneration09.pdf")            
        try:
            print "opening %s"% doc
            localsettings.openPDF(doc)
        except Exception, e:
            print Exception, e
            om_gui.advise(_("Error opening PDF file"), 2)

def chooseFeescale(om_gui, i):
    '''
    receives signals from the choose feescale combobox
    acts on the fee table
    arg will be the chosen index
    '''
    table = localsettings.FEETABLES.tables[i]
    if table.endDate == None:
        end = _("IN CURRENT USE")
    else:
        end = localsettings.formatDate(table.endDate) 
    om_gui.ui.feeScale_label.setText("<b>%s</b> %s - %s"% (
    table.description, 
    localsettings.formatDate(table.startDate), end)) 
    
    om_gui.ui.feesearch_results_label.setText("")
            
    try:
        om_gui.ui.feeScales_treeView.setModel(om_gui.fee_models[i]) 
    except IndexError:
        print i, len(om_gui.fee_models)
        om_gui.advise(_("fee table error"),2)

def adjustTable(om_gui, index):
    tv = om_gui.ui.feeScales_treeView
    for col in range(tv.model().columnCount(index)):
        if col == 3 and not om_gui.ui.actionShow_Geek_Column.isChecked():
            tv.setColumnWidth(3, 0)
        else:
            tv.resizeColumnToContents(col)
    #usercolumn is unmanageably wide now
    tv.setColumnWidth(1, 80)
    
def expandFees(om_gui):
    '''
    expands/contracts the fees treewidget
    dependent on the state of the feeExpand_radioButton
    '''
    if om_gui.ui.feeExpand_radioButton.isChecked():
        om_gui.ui.feeScales_treeView.expandAll()
        if not om_gui.ui.actionShow_Geek_Column.isChecked():
            om_gui.ui.feeScales_treeView.setColumnWidth(3, 0)
    else:
        om_gui.ui.feeScales_treeView.collapseAll()
    
def makeBadDebt(om_gui):
    '''
    write off the debt (stops cluttering up the accounts table)
    '''
    result = QtGui.QMessageBox.question(om_gui, "Confirm",
    "Move this patient to Bad Debt Status?",
    QtGui.QMessageBox.No | QtGui.QMessageBox.Yes,
    QtGui.QMessageBox.Yes )
    if result == QtGui.QMessageBox.Yes:
        #--what is owed
        om_gui.pt.money11 = om_gui.pt.fees
        om_gui.pt.resetAllMonies()
        om_gui.pt.status = "BAD DEBT"
        om_gui.ui.notesEnter_textEdit.setText(
        "changed patients status to BAD DEBT")

        om_gui.updateStatus()
        om_gui.updateDetails()

def populateAccountsTable(om_gui):
    rows = accounts.details()
    om_gui.ui.accounts_tableWidget.clear()
    om_gui.ui.accounts_tableWidget.setSortingEnabled(False)
    om_gui.ui.accounts_tableWidget.setRowCount(len(rows))
    headers = ("Dent", "Serialno", "", "First", "Last", "DOB", "Memo",
    "Last Appt", "Last Bill", "Type", "Number", "T/C", "Fees", "A", "B",
    "C")

    om_gui.ui.accounts_tableWidget.setColumnCount(len(headers))
    om_gui.ui.accounts_tableWidget.setHorizontalHeaderLabels(headers)
    om_gui.ui.accounts_tableWidget.verticalHeader().hide()
    rowno = 0
    total = 0
    for row in rows:
        for col in range(len(row)):
            d = row[col]
            if d != None or col == 11:
                item = QtGui.QTableWidgetItem()
                if col == 0:
                    item.setText(localsettings.ops.get(d))
                elif col in (5, 7, 8):
                    item.setData(QtCore.Qt.DisplayRole,
                    QtCore.QVariant(QtCore.QDate(d)))
                elif col == 12:
                    total += d
                    #--jump through hoops to make the string sortable!
                    money = QtCore.QVariant(QtCore.QString("%L1").\
                    arg(float(d/100), 8, "f", 2))

                    item.setData(QtCore.Qt.DisplayRole, money)
                    item.setTextAlignment(
                    QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)

                    #item.setText(localsettings.formatMoney(d))

                elif col == 11:
                    if d > 0:
                        item.setText("N")
                    else:
                        item.setText("Y")
                else:
                    item.setText(str(d).title())
                om_gui.ui.accounts_tableWidget.setItem(rowno, col, item)
        for col in range(13, 16):
            item = QtGui.QTableWidgetItem()
            item.setCheckState(QtCore.Qt.Unchecked)
            om_gui.ui.accounts_tableWidget.setItem(rowno, col, item)
        rowno += 1
    om_gui.ui.accounts_tableWidget.sortItems(7, QtCore.Qt.DescendingOrder)
    om_gui.ui.accounts_tableWidget.setSortingEnabled(True)
    #om_gui.ui.accounts_tableWidget.update()
    for i in range(om_gui.ui.accounts_tableWidget.columnCount()):
        om_gui.ui.accounts_tableWidget.resizeColumnToContents(i)
    om_gui.ui.accountsTotal_doubleSpinBox.setValue(total / 100)