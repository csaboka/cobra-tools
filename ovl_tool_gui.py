import os
import io
import sys
import traceback
import time
from PyQt5 import QtWidgets, QtGui, QtCore

from pyffi_ext.formats.ovl import OvlFormat
from util import widgets, config
from modules import extract, inject,hasher

class MainWindow(widgets.MainWindow):

	def __init__(self):
		widgets.MainWindow.__init__(self, "OVL Tool", )
		
		self.ovl_data = OvlFormat.Data()
		self.file_src = ""

		supported_types = ("DDS", "PNG", "MDL2", "TXT", "FGM", "FDB", "MATCOL", "XMLCONFIG","ASSETPKG","LUA")
		self.filter = "Supported files ({})".format( " ".join("*."+t for t in supported_types) )
		
		mainMenu = self.menuBar() 
		fileMenu = mainMenu.addMenu('File')
		editMenu = mainMenu.addMenu('Edit')
		helpMenu = mainMenu.addMenu('Help')
		button_data = ( (fileMenu, "Open", self.open_ovl, "CTRL+O"),
						(fileMenu, "Save", self.save_ovl, "CTRL+S"),
						(fileMenu, "Exit", self.close, ""),
						(editMenu, "Unpack", self.extract_all, "CTRL+U"),
						(editMenu, "Extract text", self.extract_text, ""),
						(editMenu, "Inject", self.inject, "CTRL+I"),
						(editMenu, "Inject text", self.inject_text, ""),
						(editMenu, "Hash", self.hasher,"CTRL+H"),
						(helpMenu, "Report Bug", self.report_bug, ""),
						(helpMenu, "Documentation", self.online_support, "") )
		self.add_to_menu(button_data)

		tooltips = ( "Load an OVL archive whose files you want to modify.",
					 "Save the OVL file you do not want to merge.",
					 "Unpack all known files from the OVL into the selected folder.",
					 "Load files to inject into the opened OVL archive.")

		self.e_ovl_name = QtWidgets.QLineEdit(self)
		self.e_ovl_name.setToolTip("The name of the OVL file that is currently open.")
		self.e_ovl_name.setReadOnly(True)

		self.e_name_pairs = [ (QtWidgets.QLineEdit("old"), QtWidgets.QLineEdit("new")) for i in range(3) ]
        
		# toggles
		self.t_write_dds = QtWidgets.QCheckBox("Save DDS")
		self.t_write_dds.setToolTip("By default, DDS files are converted to PNG and back on the fly.")
		self.t_write_dds.setChecked(False)
		
		self.t_write_dat = QtWidgets.QCheckBox("Save DAT")
		self.t_write_dat.setToolTip("Writes decompressed archive streams to DAT files for debugging.")
		self.t_write_dat.setChecked(False)
		self.t_write_dat.stateChanged.connect(self.load_ovl)

		self.t_write_frag_log = QtWidgets.QCheckBox("Save Frag Log")
		self.t_write_frag_log.setToolTip("For devs.")
		self.t_write_frag_log.setChecked(False)
		self.t_write_frag_log.stateChanged.connect(self.load_ovl)

		self.qgrid = QtWidgets.QGridLayout()
		self.qgrid.addWidget(self.e_ovl_name, 0, 0, 1, 2)
		self.qgrid.addWidget(self.t_write_dds, 1, 0)
		self.qgrid.addWidget(self.t_write_dat, 2, 0)
		self.qgrid.addWidget(self.t_write_frag_log, 3, 0)
		start = 4
		for i, (old, new) in enumerate(self.e_name_pairs):
			self.qgrid.addWidget(old, start+i, 0)
			self.qgrid.addWidget(new, start+i, 1)

		self.central_widget.setLayout(self.qgrid)
	
	@property
	def commands(self,):
		# get those commands that are set to True
		return [ x for x in ("write_dat", "write_frag_log") if getattr(self, x)]
	
	def update_commands(self):
		# at some point, just set commands to archive and trigger changes there
		if self.ovl_name:
			self.ovl_data.commands = self.commands

	@property
	def ovl_name(self,):
		return self.e_ovl_name.text()

	@property
	def write_dds(self,):
		return self.t_write_dds.isChecked()
	
	@property
	def write_dat(self,):
		return self.t_write_dat.isChecked()

	@property
	def write_frag_log(self,):
		return self.t_write_frag_log.isChecked()

	def open_ovl(self):
		"""Just a wrapper so we can also reload via code"""
		self.file_src = QtWidgets.QFileDialog.getOpenFileName(self, 'Load OVL', self.cfg["dir_ovls_in"], "OVL files (*.ovl)")[0]
		self.load_ovl()

	def load_ovl(self):
		if self.file_src:
			self.cfg["dir_ovls_in"], ovl_name = os.path.split(self.file_src)
			start_time = time.time()
			try:
				with open(self.file_src, "rb") as ovl_stream:
					self.ovl_data.read(ovl_stream, file=self.file_src, commands=self.commands)
				self.e_ovl_name.setText(ovl_name)
			except Exception as ex:
				traceback.print_exc()
				widgets.showdialog( str(ex) )
				print(ex)
			print(f"Done in {time.time()-start_time:.2f} seconds!")
		
	def save_ovl(self):
		if self.ovl_name:
			file_src = QtWidgets.QFileDialog.getSaveFileName(self, 'Save OVL', os.path.join(self.cfg["dir_ovls_out"], self.ovl_name), "OVL files (*.ovl)",)[0]
			if file_src:
				self.cfg["dir_ovls_out"], ovl_name = os.path.split(file_src)
				# just a dummy stream
				with io.BytesIO() as ovl_stream:
					self.ovl_data.write(ovl_stream, file_path=file_src)
				print("Done!")
			
	def extract_all(self):
		if self.ovl_name:
			self.cfg["dir_extract"] = QtWidgets.QFileDialog.getExistingDirectory(self, 'Output folder', self.cfg["dir_extract"], )
			if self.cfg["dir_extract"]:
				dir = self.cfg["dir_extract"]
				# create output dir
				try:
					os.makedirs(dir, exist_ok=True)
					for archive in self.ovl_data.archives:
						archive.dir = dir
						extract.extract(archive, self.write_dds)
					print("Done!")
				except Exception as ex:
					traceback.print_exc()
					widgets.showdialog( str(ex) )
					print(ex)
		else:
			widgets.showdialog( "You must open an OVL file before you can extract files!" )

	def extract_text(self):
		if self.ovl_name:
			target_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Save text', filter="Text files (*.txt)")[0]
			if target_path:
				try:
					extract.extract_for_localization(self.ovl_data.archives, target_path)
				except Exception as ex:
					traceback.print_exc()
					widgets.showdialog( str(ex) )
					print(ex)
		else:
			widgets.showdialog( "You must open an OVL file before you can extract text!")

	def inject(self):
		if self.ovl_name:
			files = QtWidgets.QFileDialog.getOpenFileNames(self, 'Inject files', self.cfg["dir_inject"], self.filter)[0]
			if files:
				self.cfg["dir_inject"] = os.path.dirname(files[0])
			try:
				inject.inject( self.ovl_data, files, self.write_dds )
			except Exception as ex:
				traceback.print_exc()
				widgets.showdialog( str(ex) )
			print("Done!")
		else:
			widgets.showdialog( "You must open an OVL file before you can inject files!" )

	def inject_text(self):
		if self.ovl_name:
			source_path = QtWidgets.QFileDialog.getOpenFileName(self, "Inject text", filter="Text files (*.txt)")[0]
			if source_path:
				try:
					inject.inject_localization(self.ovl_data, source_path)
				except Exception as ex:
					traceback.print_exc()
					widgets.showdialog(str(ex))
					print(ex)
		else:
			widgets.showdialog( "You must open an OVL file before you can inject text!" )

	def hasher(self):
		if self.ovl_name:
			names = [ (tup[0].text(), tup[1].text()) for tup in self.e_name_pairs ]
			for archive in self.ovl_data.archives:
				hasher.dat_hasher(archive, names, self.ovl_data.header.files,self.ovl_data.header.textures)


		else:
			widgets.showdialog( "You must open an OVL file before you can extract files!" )

			       

if __name__ == '__main__':
	widgets.startup( MainWindow )
