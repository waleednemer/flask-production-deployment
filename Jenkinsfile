
pipeline {
    agent any

    environment {
        DOCKER_IMAGE = 'waleednemer/flask-production-deployment'
        DOCKER_CREDENTIALS = 'dockerhub-credentials'
        PYTHON_VENV = 'venv'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        // ==========================================
        // 1. CHECKOUT
        // ==========================================

        stage('Checkout') {
            steps {
                echo 'Checking out source code...'

                checkout scm

                sh '''
                    echo "Build Number: $BUILD_NUMBER"
                    echo "Git Branch: $BRANCH_NAME"

                    echo "Commit:"
                    git log -1 --oneline

                    echo "Project files:"
                    ls -la

                    test -f requirements.txt
                    test -f Dockerfile
                '''
            }
        }

        // ==========================================
        // 2. INSTALL DEPENDENCIES
        // ==========================================

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv "$PYTHON_VENV"

                    . "$PYTHON_VENV/bin/activate"

                    python -m pip install --upgrade pip

                    pip install -r requirements.txt
                '''
            }
        }

        // ==========================================
        // 3. RUN TESTS
        // ==========================================

        stage('Run Tests') {
            steps {
                sh '''
                    . "$PYTHON_VENV/bin/activate"

                    python -m pytest -v
                '''
            }
        }

        // ==========================================
        // 4. BUILD DOCKER IMAGE
        // ==========================================

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build \
                        -t "$DOCKER_IMAGE:$BUILD_NUMBER" \
                        -t "$DOCKER_IMAGE:latest" \
                        .

                    echo "Docker images built successfully."

                    docker images "$DOCKER_IMAGE"
                '''
            }
        }

        // ==========================================
        // 5. LOGIN TO DOCKER HUB
        // ==========================================

        stage('Login to Docker Hub') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: "${DOCKER_CREDENTIALS}",
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    )
                ]) {
                    sh '''
                        set +x

                        echo "$DOCKER_PASSWORD" | docker login \
                            --username "$DOCKER_USERNAME" \
                            --password-stdin
                    '''
                }
            }
        }

        // ==========================================
        // 6. PUSH DOCKER IMAGES
        // ==========================================

        stage('Push Docker Images') {
            steps {
                sh '''
                    docker push "$DOCKER_IMAGE:$BUILD_NUMBER"

                    docker push "$DOCKER_IMAGE:latest"

                    echo "Images pushed successfully."
                '''
            }
        }

        // ==========================================
        // 7. VERIFY DOCKER IMAGES
        // ==========================================

        stage('Verify Docker Images') {
            steps {
                sh '''
                    docker image inspect "$DOCKER_IMAGE:$BUILD_NUMBER"

                    docker image inspect "$DOCKER_IMAGE:latest"

                    echo "Docker image verification successful."
                '''
            }
        }

        // ==========================================
        // 8. DEPLOY APPLICATION
        // ==========================================

        stage('Deploy Application') {
            steps {
                sh '''
                    set -eu

                    NEW_CONTAINER="flask-candidate-${BUILD_NUMBER}"
                    OLD_CONTAINER="flask-production-container"
                    BACKUP_CONTAINER="flask-production-backup-${BUILD_NUMBER}"

                    CANDIDATE_PORT=$((15000 + BUILD_NUMBER))

                    echo "=================================="
                    echo "DEPLOYING VERSION ${BUILD_NUMBER}"
                    echo "=================================="

                    # Pull new image
                    docker pull "$DOCKER_IMAGE:$BUILD_NUMBER"

                    # Remove old candidate if exists
                    docker rm -f "$NEW_CONTAINER" 2>/dev/null || true

                    # Start candidate container
                    docker run -d \
                        --name "$NEW_CONTAINER" \
                        -p "${CANDIDATE_PORT}:5000" \
                        "$DOCKER_IMAGE:$BUILD_NUMBER"

                    echo "Testing candidate application..."

                    HEALTH_OK=false

                    for i in $(seq 1 15); do
                        if curl -fsS \
                            "http://localhost:${CANDIDATE_PORT}/health"; then

                            HEALTH_OK=true
                            break
                        fi

                        sleep 2
                    done

                    # Candidate health check
                    if [ "$HEALTH_OK" != "true" ]; then
                        echo "Candidate health check failed!"

                        docker logs "$NEW_CONTAINER"

                        docker rm -f "$NEW_CONTAINER"

                        exit 1
                    fi

                    echo "Candidate health check passed."

                    # Remove candidate
                    docker rm -f "$NEW_CONTAINER"

                    # Backup previous production container
                    if docker ps -a --format '{{.Names}}' | grep -qx "$OLD_CONTAINER"; then

                        if docker ps -a --format '{{.Names}}' | grep -qx "$BACKUP_CONTAINER"; then
                            docker rm -f "$BACKUP_CONTAINER"
                        fi

                        docker stop "$OLD_CONTAINER" || true

                        docker rename "$OLD_CONTAINER" "$BACKUP_CONTAINER"

                        echo "Previous version backed up."
                    fi

                    # Start new production container
                    if ! docker run -d \
                        --name "$OLD_CONTAINER" \
                        -p 5000:5000 \
                        --restart unless-stopped \
                        "$DOCKER_IMAGE:$BUILD_NUMBER"; then

                        echo "New production container failed!"

                        if docker ps -a --format '{{.Names}}' | grep -qx "$BACKUP_CONTAINER"; then
                            docker rename "$BACKUP_CONTAINER" "$OLD_CONTAINER"
                            docker start "$OLD_CONTAINER"
                        fi

                        exit 1
                    fi

                    echo "Checking production health..."

                    HEALTH_OK=false

                    for i in $(seq 1 15); do
                        if curl -fsS http://localhost:5000/health; then

                            HEALTH_OK=true
                            break
                        fi

                        sleep 2
                    done

                    # Production health check
                    if [ "$HEALTH_OK" != "true" ]; then

                        echo "Production health check failed!"

                        docker logs "$OLD_CONTAINER"

                        docker rm -f "$OLD_CONTAINER"

                        # Rollback
                        if docker ps -a --format '{{.Names}}' | grep -qx "$BACKUP_CONTAINER"; then

                            docker rename "$BACKUP_CONTAINER" "$OLD_CONTAINER"

                            docker start "$OLD_CONTAINER"

                            echo "Rollback completed."
                        else
                            echo "No previous version available for rollback!"
                        fi

                        exit 1
                    fi

                    echo "=================================="
                    echo "DEPLOYMENT SUCCESSFUL"
                    echo "=================================="

                    echo "Version: ${BUILD_NUMBER}"
                    echo "Container: ${OLD_CONTAINER}"
                    echo "Port: 5000"

                    docker ps
                '''
            }
        }
    }

    // ==========================================
    // POST ACTIONS
    // ==========================================

    post {

        always {
            sh '''
                docker logout || true
            '''

            echo 'Pipeline execution finished.'
        }

        success {
            echo '======================================'
            echo 'PIPELINE COMPLETED SUCCESSFULLY'
            echo '======================================'

            echo "Docker Image: ${DOCKER_IMAGE}:${BUILD_NUMBER}"
            echo "Latest Image: ${DOCKER_IMAGE}:latest"
            echo 'Deployment completed successfully.'
        }

        failure {
            echo '======================================'
            echo 'PIPELINE FAILED'
            echo '======================================'

            echo 'Check Console Output for details.'
            echo 'Deployment may have been rolled back.'
        }
    }
}
