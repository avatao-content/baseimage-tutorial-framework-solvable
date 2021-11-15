FROM avatao/debian:buster

RUN apt-get --allow-releaseinfo-change-suite update && \
    apt-get install -qy --no-install-recommends \
        supervisor

RUN pip3 install \
        pyzmq==19.0.2 \
        tornado==6.0.4 \
        pyyaml \
        tfwsdk
        
COPY tutorial /.tutorial
COPY etc /etc

RUN chown -R user:user /home/user

ONBUILD COPY solvable/tutorial /.tutorial
ONBUILD RUN python3 /.tutorial/create_app_from_yml.py && chown -R root:root /.tutorial
ONBUILD VOLUME ["/.tutorial"]

CMD exec supervisord --nodaemon --configuration /etc/supervisor/supervisord.conf
