FROM avatao/debian:buster

RUN apt-get update && \
    apt-get install -qy --no-install-recommends \
        supervisor

RUN pip3 install \
        pyzmq==19.0.2 \
        tornado==6.0.4 \
        pyyaml \
        git+https://github.com/avatao-content/tfwsdk-python.git@318ce905398c988831001d72c47fb437f282228a
        
COPY tutorial /home/user/tutorial
COPY etc /etc

RUN chown -R user:user /home/user

ONBUILD RUN python3 /home/user/tutorial/create_app_from_yml.py
ONBUILD VOLUME ["/home/user"]

CMD exec supervisord --nodaemon --configuration /etc/supervisor/supervisord.conf