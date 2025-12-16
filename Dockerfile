# Paper Minecraft Server for Railway
# Uses your existing server files
FROM eclipse-temurin:21-jre-alpine

# Install required tools
RUN apk add --no-cache curl bash

# Set working directory
WORKDIR /server

# Copy your existing server files
COPY . /server/

# Make sure EULA is accepted
RUN echo "eula=true" > /server/eula.txt

# Set memory allocation (adjust based on Railway plan)
ENV MEMORY_MIN=1G
ENV MEMORY_MAX=2G

# Expose Minecraft port (Java)
EXPOSE 25565

# Expose Geyser port (Bedrock)
EXPOSE 19132/udp

# Create startup script
RUN echo '#!/bin/bash' > /server/start.sh && \
    echo 'java -Xms${MEMORY_MIN} -Xmx${MEMORY_MAX} \' >> /server/start.sh && \
    echo '  -XX:+UseG1GC \' >> /server/start.sh && \
    echo '  -XX:+ParallelRefProcEnabled \' >> /server/start.sh && \
    echo '  -XX:MaxGCPauseMillis=200 \' >> /server/start.sh && \
    echo '  -XX:+UnlockExperimentalVMOptions \' >> /server/start.sh && \
    echo '  -XX:+DisableExplicitGC \' >> /server/start.sh && \
    echo '  -XX:+AlwaysPreTouch \' >> /server/start.sh && \
    echo '  -XX:G1NewSizePercent=30 \' >> /server/start.sh && \
    echo '  -XX:G1MaxNewSizePercent=40 \' >> /server/start.sh && \
    echo '  -XX:G1HeapRegionSize=8M \' >> /server/start.sh && \
    echo '  -XX:G1ReservePercent=20 \' >> /server/start.sh && \
    echo '  -XX:G1HeapWastePercent=5 \' >> /server/start.sh && \
    echo '  -XX:G1MixedGCCountTarget=4 \' >> /server/start.sh && \
    echo '  -XX:InitiatingHeapOccupancyPercent=15 \' >> /server/start.sh && \
    echo '  -XX:G1MixedGCLiveThresholdPercent=90 \' >> /server/start.sh && \
    echo '  -XX:G1RSetUpdatingPauseTimePercent=5 \' >> /server/start.sh && \
    echo '  -XX:SurvivorRatio=32 \' >> /server/start.sh && \
    echo '  -XX:+PerfDisableSharedMem \' >> /server/start.sh && \
    echo '  -XX:MaxTenuringThreshold=1 \' >> /server/start.sh && \
    echo '  -Dusing.aikars.flags=https://mcflags.emc.gs \' >> /server/start.sh && \
    echo '  -Daikars.new.flags=true \' >> /server/start.sh && \
    echo '  -jar server.jar nogui' >> /server/start.sh && \
    chmod +x /server/start.sh

# Start the server
CMD ["/bin/bash", "/server/start.sh"]
