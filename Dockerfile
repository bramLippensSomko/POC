FROM docker.somko.be/odoo/enterprise:18.0_latest
USER root

ADD requirements.txt /
RUN pip3 install --ignore-installed -r /requirements.txt

COPY custom /mnt/repo/custom
COPY third /mnt/repo/third

USER odoo
