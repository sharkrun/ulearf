FROM busybox

EXPOSE 8881
ENV ETCDCLUSTER http://127.0.0.1:2379
# ENV MODULE_VERSION #MODULE_VERSION#
CMD export PATH=$PATH:/root

COPY  ./ssl/server.crt /root/server.crt

COPY ./conf /root/conf
COPY ./swagger /root/swagger

COPY ./ufleet-user /root
CMD chmod +x /root/ufleet-user

COPY ./reset.sh /root/reset.sh
CMD chmod +x /root/reset.sh

WORKDIR /root
CMD ["./ufleet-user"]

