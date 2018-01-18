FROM 192.168.18.250:5002/os/debian:latest
MAINTAINER "UFleet platform cluster-daemon"

USER root

############################################################
# Setup environment variables
############################################################
ENV WORK_DIR /opt
ENV CLUSTER_WORK_ROOT /opt/cluster-daemon
ENV START_SCRIPT /opt/start.sh
# ENV MODULE_VERSION #MODULE_VERSION#

############################################################

ADD src/dist/main /opt/cluster-daemon/cluster-daemon
RUN chmod +x /opt/cluster-daemon/cluster-daemon

ADD src/frame/conf /opt/cluster-daemon/conf
ADD src/trace /opt/cluster-daemon/trace


ADD start.sh $START_SCRIPT
RUN chmod +x $START_SCRIPT

# Let people know how this was built
ADD Dockerfile /root/Dockerfile



CMD $START_SCRIPT
