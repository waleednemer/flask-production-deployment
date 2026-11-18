
pipeline {
    agent any

    environment {
        DOCKER_IMAGE = 'waleednemer/flask-production-deployment'
        DOCKER_CREDENTIALS = 'dockerhub-credentials'
        PYTHON_VENV = 'venv'

        DEPLOY_CONTAINER = 'flask-production-v3'
        DEPLOY_PORT = '5011'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        // 1. Checkout
        stage('Checkout') {
            steps {
                echo 'Checking out source code...'

                checkout scm

                sh '''
                    echo "Build Number: $BUILD_NUMBER"
                    echo "Git Branch: $BRANCH_NAME"

                    git log -1 --oneline

                    ls -la

                    test -f requirements.txt
                    test -f Dockerfile
                    test -f app.py
                '''
            }
        }

        // 2. Install Dependencies
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

        // 3. Run Tests
        stage('Run Tests') {
            steps {
                sh '''
                    . "$PYTHON_VENV/bin/activate"

                    python -m pytest -v
                '''
            }
        }

        // 4. Build Docker Image
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

        // 5. Login to Docker Hub
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

        // 6. Push Docker Images
        stage('Push Docker Images') {
            steps {
                sh '''
                    docker push "$DOCKER_IMAGE:$BUILD_NUMBER"

                    docker push "$DOCKER_IMAGE:latest"

                    echo "Images pushed successfully."
                '''
            }
        }

        // 7. Verify Docker Images
        stage('Verify Docker Images') {
            steps {
                sh '''
                    docker image inspect "$DOCKER_IMAGE:$BUILD_NUMBER"

                    docker image inspect "$DOCKER_IMAGE:latest"

                    echo "Docker image verification successful."
                '''
            }
        }

        // 8. Deploy Automatically
        stage('Deploy') {
            steps {
                sh '''
                    set -eu

                    NEW_IMAGE="$DOCKER_IMAGE:$BUILD_NUMBER"

                    BACKUP_CONTAINER="${DEPLOY_CONTAINER}-rollback-${BUILD_NUMBER}"

                    HAD_OLD=false

                    echo "Starting deployment..."
                    echo "New Image: $NEW_IMAGE"
                    echo "Target Container: $DEPLOY_CONTAINER"
                    echo "Target Port: $DEPLOY_PORT"

                    # Preserve the existing test container
                    if docker container inspect "$DEPLOY_CONTAINER" >/dev/null 2>&1; then

                        echo "Existing test container found."

                        docker stop "$DEPLOY_CONTAINER"

                        docker rename "$DEPLOY_CONTAINER" "$BACKUP_CONTAINER"

                        HAD_OLD=true

                        echo "Previous container preserved for rollback."

                    else
                        echo "No existing test container found."
                    fi

                    # Start the new container
                    if ! docker run -d \
                        --name "$DEPLOY_CONTAINER" \
                        -p "$DEPLOY_PORT:5000" \
                        --restart unless-stopped \
                        "$NEW_IMAGE"; then

                        echo "New container failed to start."

                        if [ "$HAD_OLD" = true ]; then
                            docker rename "$BACKUP_CONTAINER" "$DEPLOY_CONTAINER"
                            docker start "$DEPLOY_CONTAINER"
                            echo "Previous container restored."
                        fi

                        exit 1
                    fi

                    echo "New container started successfully."

                    # Verify application health
                    HEALTHY=false

                    for attempt in $(seq 1 20); do

                        if curl -fsS "http://127.0.0.1:$DEPLOY_PORT/health" \
                            | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data.get("status") == "healthy"
' 2>/dev/null; then

                            HEALTHY=true
                            echo "Health check passed."
                            break

                        fi

                        echo "Waiting for application... attempt $attempt/20"

                        sleep 2

                    done

                    # Rollback if deployment is unhealthy
                    if [ "$HEALTHY" != true ]; then

                        echo "Deployment health check failed."

                        docker logs "$DEPLOY_CONTAINER" || true

                        docker rm -f "$DEPLOY_CONTAINER" || true

                        if [ "$HAD_OLD" = true ]; then

                            docker rename "$BACKUP_CONTAINER" "$DEPLOY_CONTAINER"

                            docker start "$DEPLOY_CONTAINER"

                            echo "Rollback completed."

                        fi

                        exit 1
                    fi

                    # Remove previous container after successful deployment
                    if [ "$HAD_OLD" = true ]; then

                        docker rm "$BACKUP_CONTAINER"

                        echo "Previous test container removed."

                    fi

                    echo "Deployment completed successfully."
                '''
            }
        }

        // 9. Verify Deployment
        stage('Verify Deployment') {
            steps {
                sh '''
                    set -eu

                    echo "Testing deployed application..."

                    python3 - <<'PY'
import json
import urllib.request

BASE_URL = "http://127.0.0.1:5011"

def get_json(path):
    url = BASE_URL + path

    with urllib.request.urlopen(url, timeout=10) as response:
        assert response.status == 200
        return json.loads(response.read().decode())

home = get_json("/")
version = get_json("/version")
health = get_json("/health")

assert home["status"] == "running"
assert version["status"] == "running"
assert health["status"] == "healthy"

assert home["version"] == version["version"]

assert home["application"] == "flask-production"
assert version["application"] == "flask-production"

print("Home endpoint: PASSED")
print("Version endpoint: PASSED")
print("Health endpoint: PASSED")
print("Application version:", version["version"])
print("All deployment tests passed!")
PY

                    echo "Deployment verification successful."
                '''
            }
        }
    }

    post {

        always {
            sh '''
                docker logout || true
            '''
        }

        success {
            echo '======================================'
            echo 'PIPELINE COMPLETED SUCCESSFULLY'
            echo '======================================'

            echo "Docker Image: ${DOCKER_IMAGE}:${BUILD_NUMBER}"
            echo "Latest Image: ${DOCKER_IMAGE}:latest"
            echo "Container: ${DEPLOY_CONTAINER}"
            echo "Port: ${DEPLOY_PORT}"
            echo "Deployment: SUCCESS"
        }

        failure {
            echo '======================================'
            echo 'PIPELINE FAILED'
            echo '======================================'

            echo 'Check Jenkins Console Output.'
            echo 'Deployment may have been rolled back.'
        }
    }
}
