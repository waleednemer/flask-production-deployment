
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

        stage('Run Tests') {
            steps {
                sh '''
                    . "$PYTHON_VENV/bin/activate"

                    python -m pytest -v
                '''
            }
        }

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

        stage('Push Docker Images') {
            steps {
                sh '''
                    docker push "$DOCKER_IMAGE:$BUILD_NUMBER"

                    docker push "$DOCKER_IMAGE:latest"

                    echo "Images pushed successfully."
                '''
            }
        }

        stage('Verify Docker Images') {
            steps {
                sh '''
                    docker image inspect "$DOCKER_IMAGE:$BUILD_NUMBER"

                    docker image inspect "$DOCKER_IMAGE:latest"

                    echo "Local image verification successful."
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
        }

        failure {
            echo '======================================'
            echo 'PIPELINE FAILED'
            echo 'Check Console Output for details.'
            echo '======================================'
        }
    }
}
