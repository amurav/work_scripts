#!/bin/bash

# Add a new grammar; follows the grammar template:
# {
#   "_id" : ObjectId("5d2c43186ffe38232b6beed3"),
#   "id" : "AlphaNumeric_5cdaad837fb4026b5e3d78a1",
#   "name" : "AlphaNumeric_5cdaad837fb4026b5e3d78a1",
#   "language" : "en-US",
#   "deleted" : false,
#   "lingware" : "AlphaNumeric_5cdaad837fb4026b5e3d78a1",
#   "type" : "grxml",
#   "owner" : "5d2c2695d2adc2d4928d8b34",
#   "group" : "5d2c2695d2adc2d4928d8b34",
#   "engine" : "local",
#   "user_token" : "a6f3e1d5-5760-42ed-b591-adaf65e57b1e"
# }

echo "Creating new grammar"

function get_answer {
    read -p "$1: " answer
    echo $answer
}

email=$(get_answer "Email address: ")
userid=""
usertoken=""

# Try to find the user id and token, so we can attach them as owner credentials

username=`cat /run/secrets/mongo_username`
password=`cat /run/secrets/mongo_password`

userid=`mongo --username "${username}" --password "${password}" --authenticationDatabase admin --quiet user_admin --eval 'db.users.find ({"email":"'${email}'"},{"_id":1, "user_token": 1}).forEach (function (results) { results._id=results._id.valueOf (); printjson (results._id)})'`
usertoken=`mongo --username "${username}" --password "${password}" --authenticationDatabase admin --quiet user_admin --eval 'db.users.find ({"email":"'${email}'"},{"_id":1, "user_token": 1}).forEach (function (results) { results._id=results._id.valueOf (); printjson (results.user_token)})'`
org=`mongo --username "${username}" --password "${password}" --authenticationDatabase admin --quiet user_admin --eval 'db.users.find ({"email":"'${email}'"},{"_id":1, "user_token": 1, "org": 1}).forEach (function (results) { results._id=results._id.valueOf (); printjson (results.org)})'`

if [ "${userid}" != "undefined" ]
then
    # more questions
    grammar=$(get_answer "grammar id: ")
    lang=$(get_answer "language code: ")
    gtype=$(get_answer "grxml|lvcsr: ")
    engine=$(get_answer "mrcp engine to use: ")

    template='{"id": "'${grammar}'", "name": "'${grammar}'", "language": "'${lang}'", "deleted": false, "lingware": "'${grammar}'", "type": "'${gtype}'", "org": '${org}', "owner": '${userid}', "group": '${userid}', "engine": "'${engine}'", "user_token": '${usertoken}'}'

    echo $template > /tmp/new_grammar.json

    DB_NAME="ibuilder"
    mongoimport --username "${username}" --password "${password}" --authenticationDatabase admin --db ${DB_NAME} --collection grammars --mode upsert --file /tmp/new_grammar.json
else
    echo "User not found.  Exiting."
    exit 1;
fi
