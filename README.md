# fiberhome-mundo-admin-recovery

Recover the admin password of FiberHome GPON ONTs provisioned by **Mundo Pacífico** (Chile).

Mundo Pacífico rolled out TR-069, which rewrites the admin password on their
FiberHome ONTs and leaves customers locked out of their own device. The basic
customer account can still trigger a configuration backup, and that backup
contains the admin password. This tool automates the recovery.

Tested on a FiberHome HG6145F running firmware RP2934.

## How it works

1. Logs in with the customer account (default `user` / `user1234`).
2. Requests a configuration backup (`down_cfgfile`) and downloads it.
3. Decrypts the backup (XOR, then AES-128-ECB for the stored strings).
4. Prints the admin username and password, then logs out.

Both keys are constants in the firmware and are not device-specific.

## Requirements

- Python 3.8+
- [requests](https://pypi.org/project/requests/)
- [cryptography](https://pypi.org/project/cryptography/)

```
pip install -r requirements.txt
```

## Usage

Run it on a machine connected to the router's LAN:

```
python3 recover_admin.py
```

Options:

```
python3 recover_admin.py --host http://192.168.1.1 --user user --password user1234
python3 recover_admin.py --config usrconfig_conf.bin   # decrypt a local backup
```

Output:

```
username: admin
password: <admin-password>
```

Log in at `http://192.168.1.1/` with those credentials to get the full admin
interface.

## Limitations

- TR-069 can rotate the admin password again. Re-run the tool when the old one
  stops working.
- It needs a valid customer account and access to the router's LAN.
- Mundo Pacífico uses CGNAT; recovering the admin password does not give you a
  public IP.

## Disclaimer

For your own device only. Use it to regain access to equipment you own or are
authorized to manage.

## License

MIT. See [LICENSE](LICENSE).

---

## Español

Recupera la contraseña de administrador de las ONT GPON FiberHome aprovisionadas
por **Mundo Pacífico** (Chile).

Mundo Pacífico activó TR-069, que reescribe la contraseña de administrador de
sus ONT FiberHome y deja a los clientes fuera de su propio equipo. La cuenta
básica de cliente todavía puede generar un respaldo de configuración, y ese
respaldo contiene la contraseña de administrador. Esta herramienta automatiza
la recuperación.

### Cómo funciona

1. Inicia sesión con la cuenta de cliente (`user` / `user1234`).
2. Solicita el respaldo de configuración (`down_cfgfile`) y lo descarga.
3. Descifra el respaldo (XOR y luego AES-128-ECB para las cadenas guardadas).
4. Imprime el usuario y la contraseña de administrador, y cierra la sesión.

### Uso

```
pip install -r requirements.txt
python3 recover_admin.py
```

Opciones:

```
python3 recover_admin.py --host http://192.168.1.1 --user user --password user1234
python3 recover_admin.py --config usrconfig_conf.bin   # descifrar un respaldo local
```

Luego entra en `http://192.168.1.1/` con las credenciales obtenidas.

### Aviso

Solo para tu propio equipo. Úsalo para recuperar el acceso a equipos de tu
propiedad o que estés autorizado a administrar.
