
        stage('Deploy Application') {
            steps {
                sh '''
                    set -eu

                    NEW_CONTAINER="flask-candidate-${BUILD_NUMBER}"
                    OLD_CONTAINER="flask-production-container"
                    BACKUP_CONTAINER="flask-production-backup-${BUILD_NUMBER}"

                    CANDIDATE_PORT=$((15000 + BUILD_NUMBER))

                    echo "Starting deployment of version ${BUILD_NUMBER}"

                    # Pull latest build
                    docker pull "$DOCKER_IMAGE:$BUILD_NUMBER"

                    # Remove stale candidate if exists
                    docker rm -f "$NEW_CONTAINER" 2>/dev/null || true

                    # Start candidate on temporary port
                    docker run -d \
                        --name "$NEW_CONTAINER" \
                        -p "${CANDIDATE_PORT}:5000" \
                        "$DOCKER_IMAGE:$BUILD_NUMBER"

                    echo "Testing candidate application..."

                    HEALTH_OK=false

                    for i in $(seq 1 15); do
                        if curl -fsS "http://localhost:${CANDIDATE_PORT}/health"; then
                            HEALTH_OK=true
                            break
                        fi
                        sleep 2
                    done

                    if [ "$HEALTH_OK" != "true" ]; then
                        echo "Candidate health check failed!"
                        docker logs "$NEW_CONTAINER"
                        docker rm -f "$NEW_CONTAINER"
                        exit 1
                    fi

                    echo "Candidate health check passed."

                    # Remove temporary candidate
                    docker rm -f "$NEW_CONTAINER"

                    # Backup current production container
                    if docker ps -a --format '{{.Names}}' | grep -qx "$OLD_CONTAINER"; then

                        docker stop "$OLD_CONTAINER" || true

                        docker rename "$OLD_CONTAINER" "$BACKUP_CONTAINER"

                        echo "Previous version backed up."
                    fi

                    # Start new production version
                    if ! docker run -d \
                        --name "$OLD_CONTAINER" \
                        -p 5000:5000 \
                        --restart unless-stopped \
                        "$DOCKER_IMAGE:$BUILD_NUMBER"; then

                        echo "New container failed to start!"

                        if docker ps -a --format '{{.Names}}' | grep -qx "$BACKUP_CONTAINER"; then
                            docker rename "$BACKUP_CONTAINER" "$OLD_CONTAINER"
                            docker start "$OLD_CONTAINER"
                        fi

                        exit 1
                    fi

                    # Final production health check
                    HEALTH_OK=false

                    for i in $(seq 1 15); do
                        if curl -fsS http://localhost:5000/health; then
                            HEALTH_OK=true
                            break
                        fi
                        sleep 2
                    done

                    if [ "$HEALTH_OK" != "true" ]; then

                        echo "Production health check failed!"
                        docker logs "$OLD_CONTAINER"

                        docker rm -f "$OLD_CONTAINER"

                        # Rollback to previous version
                        if docker ps -a --format '{{.Names}}' | grep -qx "$BACKUP_CONTAINER"; then
                            docker rename "$BACKUP_CONTAINER" "$OLD_CONTAINER"
                            docker start "$OLD_CONTAINER"
                        fi

                        exit 1
                    fi

                    echo "=================================="
                    echo "DEPLOYMENT SUCCESSFUL"
                    echo "Version: ${BUILD_NUMBER}"
                    echo "Port: 5000"
                    echo "=================================="
                '''
            }
        }
