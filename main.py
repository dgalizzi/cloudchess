from sanic import Sanic
from sanic.websocket import WebSocketProtocol

import chess
import chess.engine

import json

app = Sanic()

engine = chess.engine.SimpleEngine.popen_uci("stockfish")
engine.configure({"Threads": 6})
board = chess.Board()

@app.websocket('/')
async def connect(request, ws):
    await ws.send(json.dumps({
        'msg': 'connected'
    }));

    while True:
        msg = await ws.recv()
        js = json.loads(msg)
        if js["msg"] == 'fen':
            # TODO: Real infinite analysis,
            # stopping when a new fen is requested.
            board.set_fen(js["data"])
            with engine.analysis(board) as analysis:
                for info in analysis:
                    if info.pv != None:
                        # TODO: Sometimes stockfish returns a single move.
                        # It seems to be a partial result when it hasn't
                        # finished analysis the current depth.
                        # Only show complete pvs.
                        #print(info.score.relative.score())
                        analysisResult = board.variation_san(info.pv)
                        await ws.send(json.dumps({
                            'msg': 'analysis',
                            'data': {
                                'depth': info.depth,
                                'score': info.score.relative.score()/100,
                                'pv': analysisResult
                            }
                        }))

                        # Arbitrary stop condition.
                        if info.depth == 20:
                            break

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, protocol=WebSocketProtocol)