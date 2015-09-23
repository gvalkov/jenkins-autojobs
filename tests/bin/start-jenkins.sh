#!/usr/bin/env bash
set -ux

# Verify that java, unzip and nc are in $PATH.
command -v java  &>/dev/null || { echo >&2 'error: java not found in $PATH'; exit 1 ; }
command -v nc    &>/dev/null || { echo >&2 'error: nc (netcat) not found in $PATH'; exit 1 ; }
command -v unzip &>/dev/null || { echo >&2 'error: unzip not found in $PATH'; exit 1 ; }

HERE=$(readlink -f $(dirname $0))

jenkins_war_url="http://mirrors.jenkins-ci.org/war/latest/jenkins.war"
hg_hpi_url="http://updates.jenkins-ci.org/download/plugins/mercurial/1.41/mercurial.hpi"
git_hpi_url="http://updates.jenkins-ci.org/download/plugins/git/1.1.21/git.hpi"

jenkins_home=${JENKINS_HOME:-"${HERE}/../tmp/jenkins"}
jenkins_port=${JENKINS_PORT:-"60888"}
jenkins_cport=${JENKINS_CPORT:-"60887"}
jenkins_addr=${JENKINS_ADDR:-"127.0.0.1"}

jenkins_war="${HERE}/../tmp/jenkins.war"
jenkins_cli="${HERE}/../tmp/jenkins-cli.jar"


#-----------------------------------------------------------------------------
mkdir -p $(dirname "$jenkins_war")
if [ ! -e "$jenkins_war" ]; then
    echo "Downloading jenkins.war ..."
    curl -L "$jenkins_war_url" > "$jenkins_war"
fi

if [ ! -e "$jenkins_cli" ]; then
    echo "Extracting jenkins-cli.jar ..."
    unzip -qqc "$jenkins_war" WEB-INF/jenkins-cli.jar > "$jenkins_cli"
fi

if [ $(unzip -l "$jenkins_war" | grep -E --count "plugins/(mercurial)|(git).hpi") -ne 2 ]; then
    echo "Adding git and hg plugins to jenkins.war ..."
    wget -c "$hg_hpi_url" "$git_hpi_url" -P "${HERE}/../tmp/WEB-INF/plugins"
    (cd "${HERE}/../tmp" && zip jenkins.war ./WEB-INF/plugins/*.hpi)
fi


#-----------------------------------------------------------------------------
shutdown () {
    echo 0 | nc "$jenkins_addr" "$jenkins_cport"
}
trap shutdown SIGINT SIGTERM EXIT


#-----------------------------------------------------------------------------
echo "Starting jenkins on ${jenkins_addr}:${jenkins_port} ..."
java -DJENKINS_HOME="${jenkins_home}" -jar "${jenkins_war}" \
     --httpListenAddress="${jenkins_addr}" \
     --httpPort="${jenkins_port}" \
     --controlPort="${jenkins_cport}" &

java_pid=$!
jenkins_running=1

echo "Waiting for jenkins to start ..."
for i in $(seq 10); do
    if curl --retry 5 -s "${jenkins_addr}":"${jenkins_port}" &>/dev/null; then
        jenkins_running=0
        break
    fi
    sleep 2
done

[ "$jenkins_running" -ne 0 ] && exit 1
wait $java_pid
