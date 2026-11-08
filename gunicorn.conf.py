"""Gunicorn settings for a t3.micro (2 vCPU, 1 GiB). Run by systemd (onward-orders.service)."""
bind = "0.0.0.0:8000"   # only the load balancer's security group may reach this port
workers = 2
threads = 4
timeout = 30
graceful_timeout = 20
accesslog = "-"         # journald: journalctl -u onward-orders
errorlog = "-"
