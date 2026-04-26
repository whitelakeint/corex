ssh jnpwladmin@208.109.191.251
jnpwladmin@208.109.191.251's password:
Activate the web console with: systemctl enable --now cockpit.socket

Last login: Sun Mar  1 07:42:43 2026 from 45.126.168.163
[jnpwladmin@251 ~]$


password is : e45#8deR5RZ5


[jnpwladmin@251 ~]$ pwd
/home/jnpwladmin
[jnpwladmin@251 ~]$ cd tavus/
[jnpwladmin@251 tavus]$
[jnpwladmin@251 tavus]$ pwd
/home/jnpwladmin/tavus
[jnpwladmin@251 tavus]$ ps -ef |grep python
jnpwlad+  145252       1 30 Feb23 ?        4-07:07:51 /home/jnpwladmin/tavus/venv/bin/python3.12 /home/jnpwladmin/tavus/venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8001 --reload



