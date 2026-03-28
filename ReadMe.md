/***
La forma fácil es usando install.sh 

	chmod +x install.sh
	./install.sh
	
Después, pasar al punto 9 para ejecutar la aplicación.
La forma compleja es seguir los pasos del 1 al 9.
/***
1.INSTALACIÓN DEL SISTEMA

	sudo apt install python3-pip python3-venv python3-evdev python3-tk -y

2.CREAR ENTORNO VIRTUAL

	python3 -m venv venv
	source venv/bin/activate

3.INSTALAR DEPENDENCIAS:

	pip install -r requirements.txt

4.CONFIGURAR MÓDULO UINPUT

	sudo modprobe uinput

VERIFICAR

	ls -l /dev/uinput
	
SI NO EXISTE:

	sudo modprobe uinput
	
5.CONFIGURAR PERMISOS PERMANENTES

	sudo nano /etc/udev/rules.d/99-uinput.rules
	
CONTENIDO:

	KERNEL=="uinput", GROUP="input", MODE="0660"
	
APLICAR CAMBIOS:

	sudo udevadm control --reload-rules
	sudo udevadm trigger
	
6.AGREGAR USUARIO AL GRUPO INPUT
	
	sudo usermod -aG input javis
	sudo reboot
	
7.DESPUÉS DEL REINICIO:

	groups
	
DEBE APARECER UINPUT.

8.PROBAR UINPUT SIN ROOT

	python3 - << "EOF"
	import uinput
	device = uinput.Device([uinput.KEY_A])
	print("OK: uinput funciona sin root")
	EOF

SALIDA ESPERADA:

	OK: uinput funciona sin root
	
9.EJECUTAR LA APLICACIÓN

	python3 app.py
