
pipeline {
    agent any

    environment {
        DOCKER_IMAGE = 'waleednemer/flask-production-deployment'
        DOCKER_CREDENTIALS = 'dockerhub-credentials'

        PYTHON_VENV = '.venv'

        DEPLOY_CONTAINER = 'flask-production-v3'
        DEPLOY_PORT = '5011'

        TEST_CONTAINER_PORT = '5012'
        APP_CONTAINER_PORT = '5000'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {

        // 1. Checkout
        stage('Checkout') {
            steps {
                echo 'Checking out latest source code...'

                checkout scm

                sh '''
                    set -eu

                    echo "Build Number: $BUILD_NUMBER"
                    echo "Branch: ${BRANCH_NAME:-unknown}"

                    git log -1 --oneline

                    test -f Dockerfile
                    test -f requirements.txt
                    test -f app.py

                    echo "Project files verified."
                '''
            }
        }

        // 2. Install Dependencies
        stage('Install Dependencies') {
            steps {
                sh '''
                    set -eu

                    python3 -m venv "$PYTHON_VENV"

                    . "$PYTHON_VENV/bin/activate"

                    python -m pip install --upgrade pip

                    pip install -r requirements.txt

                    # Ensure pytest is available
                    pip install pytest

                    python --version
                    pytest --version
                '''
            }
        }

        // 3. Run Tests
        stage('Run Tests') {
            steps {
                sh '''
                    set -eu

                    . "$PYTHON_VENV/bin/activate"

                    python -m pytest -v
                '''
            }
        }

        // 4. Build Docker Image
        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu

                    NEW_IMAGE="$DOCKER_IMAGE:$BUILD_NUMBER"

                    echo "Building: $NEW_IMAGE"

                    docker build \
                        --pull \
                        -t "$NEW_IMAGE" \
                        .

                    docker image inspect "$NEW_IMAGE"

                    echo "Docker build successful."
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
                        set -eu
                        set +x

                        echo "$DOCKER_PASSWORD" | docker login \
                            --username "$DOCKER_USERNAME" \
                            --password-stdin

                        echo "Docker Hub login successful."
                    '''
                }
            }
        }

        // 6. Push Versioned Image
        stage('Push Docker Image') {
            steps {
                sh '''
                    set -eu

                    NEW_IMAGE="$DOCKER_IMAGE:$BUILD_NUMBER"

                    docker push "$NEW_IMAGE"

                    echo "Versioned image pushed successfully."
                    echo "$NEW_IMAGE"
                '''
            }
        }

        // 7. Verify Docker Image
        stage('Verify Docker Image') {
            steps {
                sh '''
                    set -eu

                    NEW_IMAGE="$DOCKER_IMAGE:$BUILD_NUMBER"

                    docker pull "$NEW_IMAGE"

                    docker image inspect "$NEW_IMAGE"

                    echo "Remote image verification successful."
                '''
            }
        }

        // 8. Deploy, Test and Rollback
        stage('Deploy and Verify') {
            steps {
                sh '''
                    set -Eeuo pipefail

                    NEW_IMAGE="$DOCKER_IMAGE:$BUILD_NUMBER"

                    CANDIDATE="${DEPLOY_CONTAINER}-candidate-${BUILD_NUMBER}"

                    BACKUP="${DEPLOY_CONTAINER}-rollback-${BUILD_NUMBER}"

                    HAD_OLD=false
                    OLD_WAS_RUNNING=false
                    DEPLOY_SUCCESS=false

                    echo "=================================="
                    echo "STARTING SAFE DEPLOYMENT"
                    echo "=================================="

                    echo "Image: $NEW_IMAGE"
                    echo "Production Test Container: $DEPLOY_CONTAINER"
                    echo "Test Port: $TEST_CONTAINER_PORT"
                    echo "Deployment Port: $DEPLOY_PORT"

                    # --------------------------------
                    # Rollback function
                    # --------------------------------

                    rollback() {

                        EXIT_CODE=$?

                        if [ "$DEPLOY_SUCCESS" != true ]; then

                            echo "Deployment failed. Starting rollback..."

                            docker rm -f "$DEPLOY_CONTAINER" 2>/dev/null || true

                            if [ "$HAD_OLD" = true ]; then

                                if docker container inspect "$BACKUP" >/dev/null 2>&1; then

                                    docker rename "$BACKUP" "$DEPLOY_CONTAINER"

                                    if [ "$OLD_WAS_RUNNING" = true ]; then
                                        docker start "$DEPLOY_CONTAINER" || true
                                    fi

                                    echo "Previous container restored."

                                elif docker container inspect "$DEPLOY_CONTAINER" >/dev/null 2>&1; then

                                    if [ "$OLD_WAS_RUNNING" = true ]; then
                                        docker start "$DEPLOY_CONTAINER" || true
                                    fi

                                    echo "Previous container recovered."

                                fi
                            fi

                        fi

                        docker rm -f "$CANDIDATE" 2>/dev/null || true

                        exit "$EXIT_CODE"
                    }

                    trap rollback EXIT

                    # --------------------------------
                    # Check container names
                    # --------------------------------

                    if docker container inspect "$BACKUP" >/dev/null 2>&1; then
                        echo "Backup container already exists."
                        exit 1
                    fi

                    docker rm -f "$CANDIDATE" 2>/dev/null || true

                    # --------------------------------
                    # Start candidate container
                    # --------------------------------

                    echo "Starting candidate container..."

                    docker run -d \
                        --name "$CANDIDATE" \
                        -p "$TEST_CONTAINER_PORT:$APP_CONTAINER_PORT" \
                        "$NEW_IMAGE"

                    # --------------------------------
                    # Candidate health check
                    # --------------------------------

                    HEALTHY=false

                    for attempt in $(seq 1 20); do

                        if curl -fsS \
                            "http://127.0.0.1:$TEST_CONTAINER_PORT/health" \
                            | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data.get("status") == "healthy"
' 2>/dev/null; then

                            HEALTHY=true
                            echo "Candidate health check passed."
                            break

                        fi

                        echo "Waiting for candidate: $attempt/20"

                        sleep 2

                    done

                    if [ "$HEALTHY" != true ]; then
                        docker logs "$CANDIDATE" || true
                        echo "Candidate health check failed."
                        exit 1
                    fi

                    # --------------------------------
                    # Verify candidate endpoints
                    # --------------------------------

                    python3 - "$TEST_CONTAINER_PORT" <<'PY'
import json
import sys
import urllib.request

port = sys.argv[1]
base = f"http://127.0.0.1:{port}"

def get_json(path):
    with urllib.request.urlopen(base + path, timeout=10) as response:
        assert response.status == 200
        return json.loads(response.read().decode())

home = get_json("/")
health = get_json("/health")
version = get_json("/version")

assert home["status"] == "running"
assert health["status"] == "healthy"
assert version["status"] == "running"

assert home["application"] == "flask-production"
assert version["application"] == "flask-production"

assert home["version"] == version["version"]

print("Candidate home: PASSED")
print("Candidate health: PASSED")
print("Candidate version: PASSED")
print("Version:", version["version"])
PY

                    echo "Candidate passed all tests."

                    # --------------------------------
                    # Preserve existing container
                    # --------------------------------

                    if docker container inspect "$DEPLOY_CONTAINER" >/dev/null 2>&1; then

                        HAD_OLD=true

                        OLD_WAS_RUNNING=$(docker inspect \
                            -f '{{.State.Running}}' "$DEPLOY_CONTAINER")

                        echo "Preserving previous container..."

                        if [ "$OLD_WAS_RUNNING" = true ]; then
                            docker stop "$DEPLOY_CONTAINER"
                        fi

                        docker rename "$DEPLOY_CONTAINER" "$BACKUP"

                        echo "Previous container preserved."

                    else
                        echo "No previous deployment found."
                    fi

                    # --------------------------------
                    # Start new deployment
                    # --------------------------------

                    echo "Starting new deployment..."

                    docker run -d \
                        --name "$DEPLOY_CONTAINER" \
                        -p "$DEPLOY_PORT:$APP_CONTAINER_PORT" \
                        --restart unless-stopped \
                        "$NEW_IMAGE"

                    # --------------------------------
                    # Final deployment health check
                    # --------------------------------

                    HEALTHY=false

                    for attempt in $(seq 1 20); do

                        if curl -fsS \
                            "http://127.0.0.1:$DEPLOY_PORT/health" \
                            | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data.get("status") == "healthy"
' 2>/dev/null; then

                            HEALTHY=true
                            echo "Deployment health check passed."
                            break

                        fi

                        echo "Waiting for deployment: $attempt/20"

                        sleep 2

                    done

                    if [ "$HEALTHY" != true ]; then
                        docker logs "$DEPLOY_CONTAINER" || true
                        echo "Final health check failed."
                        exit 1
                    fi

                    # --------------------------------
                    # Verify final deployment
                    # --------------------------------

                    python3 - "$DEPLOY_PORT" <<'PY'
import json
import sys
import urllib.request

port = sys.argv[1]
base = f"http://127.0.0.1:{port}"

def get_json(path):
    with urllib.request.urlopen(base + path, timeout=10) as response:
        assert response.status == 200
        return json.loads(response.read().decode())

home = get_json("/")
health = get_json("/health")
version = get_json("/version")

assert home["status"] == "running"
assert health["status"] == "healthy"
assert version["status"] == "running"

assert home["application"] == "flask-production"
assert version["application"] == "flask-production"

assert home["version"] == version["version"]

print("Production test: PASSED")
print("Health check: PASSED")
print("Version check: PASSED")
print("Application version:", version["version"])
PY

                    # --------------------------------
                    # Deployment successful
                    # --------------------------------

                    DEPLOY_SUCCESS=true

                    trap - EXIT

                    docker rm -f "$CANDIDATE" || true

                    # Remove backup only after successful verification

                    if [ "$HAD_OLD" = true ]; then

                        docker rm "$BACKUP" || {
                            echo "WARNING: Old backup could not be removed."
                        }

                    fi

                    echo "=================================="
                    echo "DEPLOYMENT COMPLETED SUCCESSFULLY"
                    echo "=================================="

                    echo "Image: $NEW_IMAGE"
                    echo "Container: $DEPLOY_CONTAINER"
                    echo "Port: $DEPLOY_PORT"
                '''
            }
        }

        // 9. Publish Latest Tag
        stage('Publish Latest Image') {
            steps {
                sh '''
                    set -eu

                    NEW_IMAGE="$DOCKER_IMAGE:$BUILD_NUMBER"
                    LATEST_IMAGE="$DOCKER_IMAGE:latest"

                    docker tag "$NEW_IMAGE" "$LATEST_IMAGE"

                    docker push "$LATEST_IMAGE"

                    echo "Latest image updated successfully."
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
            echo 'Check Docker container status.'
            echo 'Check application logs.'
        }

        aborted {
            echo 'Pipeline was aborted.'
            echo 'Check the deployment and backup containers manually.'
        }
    }
}
