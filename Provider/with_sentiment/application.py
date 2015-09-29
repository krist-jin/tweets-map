from flask import Flask, render_template, Response
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.socketio import SocketIO, emit
from sqlalchemy.dialects import mysql
import json
import redis
from ast import literal_eval


application = Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://krist:jinbo0321@kristdb.cpoee5a9mjb2.us-east-1.rds.amazonaws.com:3306/kristdb'
application.debug = True
db = SQLAlchemy(application)
redis = redis.StrictRedis(host='localhost', port=6379, db=0)
socketio = SocketIO(application)


class Tweet(db.Model):
    __tablename__ = 'Tweet'
    id = db.Column(mysql.BIGINT, primary_key=True)
    text = db.Column(db.TEXT, nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)
    lon = db.Column(db.FLOAT, nullable=False)
    lat = db.Column(db.FLOAT, nullable=False)
    hashtag = db.Column(db.String(255))


@application.route('/', methods=['GET'])
@application.route('/index', methods=['GET'])
def index():
    return render_template('map.html')


@application.route('/mode/history/keyword/', methods=['GET'])
@application.route('/mode/history/keyword/<keyword>', methods=['GET'])
def handle_history(keyword=""):
    twData = []
    if not keyword:  # user does not enter a keyword
        tweets = db.engine.execute("select lat, lon from Tweet_less")
    else:
        tweets = db.engine.execute("select lat, lon from Tweet_less where text like %s", ("%"+keyword+"%",))
    for t in tweets:
        tmpDict = {"lon":t.lon, "lat":t.lat}
        twData.append(tmpDict)
    return json.dumps(twData)


@socketio.on('keyword')
def handle_realtime_connect(keyword):
    print('received keyword: ' + keyword)
    pubsub = redis.pubsub()
    pubsub.subscribe('sentiment-tweet')
    tweets = pubsub.listen()
    while True:
        try:
            message = tweets.next()
            raw_tweet = message.get('data')
            if not raw_tweet:
                continue

            tweet = None
            if str(raw_tweet)[0]=='"' or str(raw_tweet)[0]=='"':  # sns message has backslash in it
                tweet = json.loads(str(raw_tweet.decode('string_escape'))[1:-1])
            else:
                tweet = json.loads(str(raw_tweet))
            if not isinstance(tweet, dict):
                continue

            text = tweet.get('text')
            lon = tweet.get('lon')
            lat = tweet.get('lat')
            sentiment_score = tweet.get('sentiment_score')
            data = {"text":text,
                    "lon":lon,
                    "lat":lat,
                    "sentiment_score":sentiment_score}
            if text and lon and lat and data:
                if keyword in text:
                    emit('data_transfer', json.dumps(data))
        except Exception, e:
            emit('die', e, broadcast=True)
            pubsub.unsubscribe('twitter_raw')
            print e
            return


@socketio.on('disconnect')
def handle_realtime_disconnect():
    print('socket disconnect!')


if __name__ == '__main__':
    socketio.run(application, host='0.0.0.0', port=80)
