from flask import Flask, render_template
import chess
import chess.engine
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from threading import Lock    
app = Flask(__name__)
async_mode = None
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)

thread = None
thread_lock = Lock()

engine = chess.engine.SimpleEngine.popen_uci("stockfish")
board = chess.Board()

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@socketio.on('my_ping', namespace='/test')
def ping_pong():
    emit('my_pong')

@socketio.on('my_event', namespace='/test')
def test_message(message):
    fen = message["data"]
    print(f"Analysis for: {fen}")
    board.set_fen(fen)
    engine.configure({"Threads": 12})
    depth = 0

    with engine.analysis(board) as analysis:
        for info in analysis:
            # print(info.get("score"), info.get("pv"))

            if info.pv != None:
                print(f"pv {info.pv}")
                analysisResult = board.variation_san(info.pv)
                result = { 'data': analysisResult, 'depth': info.depth }
                print(f"Result {result}")
                emit('my_response', result)
                # Arbitrary stop condition.
                if info.depth == 20:
                    return


    # info = engine.analyse(board, chess.engine.Limit(time=5))

@app.route('/<path:fen>')
def hello_world(fen):
    board.set_fen(fen)
    engine.configure({"Threads": 12})
    info = engine.analyse(board, chess.engine.Limit(time=5))
    return board.variation_san(info.pv)

if __name__ == '__main__':
    socketio.run(app, debug=True)