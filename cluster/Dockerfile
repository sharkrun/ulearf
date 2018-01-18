FROM 192.168.18.250:5002/os/debian:latest
MAINTAINER "UFleet platform cluster"

USER root

############################################################
# Setup environment variables
############################################################
ENV WORK_DIR /opt
ENV CLUSTER_WORK_ROOT /opt/cluster
ENV START_SCRIPT /opt/start.sh
# ENV MODULE_VERSION #MODULE_VERSION#

############################################################



ADD src/dist/main /opt/cluster/cluster
RUN chmod +x /opt/cluster/cluster

ADD src/frame/conf /opt/cluster/conf
ADD src/trace /opt/cluster/trace

ADD wwwroot $WORK_DIR/wwwroot
ADD swagger $WORK_DIR/swagger

ADD start.sh $START_SCRIPT
RUN chmod +x $START_SCRIPT

# Let people know how this was built
ADD Dockerfile /root/Dockerfile


EXPOSE 8885

CMD $START_SCRIPT
