import asyncio

from sanic import Sanic
from sanic.websocket import WebSocketProtocol
from websockets.exceptions import ConnectionClosedOK

import chess
import chess.engine

import json

app = Sanic("Cloudchess")

# TODO: Maybe decouple the websocket from this function
# How? A callback?
async def infiniteAnalysis(engine, board, ws):
    with await engine.analysis(board) as analysis:
        async for info in analysis:
            if info.pv != None:
                # TODO: Sometimes stockfish returns a single move.
                # It seems to be a partial result when it hasn't
                # finished analysis the current depth.
                # Only show complete pvs.
                analysisResult = board.variation_san(info.pv)

                try:
                    await ws.send(json.dumps({
                        'msg': 'analysis',
                        'data': {
                            'depth': info.depth,
                            # TODO: there's no score when there's a mate
                            'score': info.score.white().score()/100,
                            'pv': analysisResult
                        }
                    }))
                except (ConnectionClosedOK):
                    await engine.quit()
                    break


#TODO: Check console error when reloading page.
@app.websocket('/')
async def connect(request, ws):
    # Initialize the board for this connection
    board = chess.Board()

    # TODO: Close the engine at some point?
    # TODO: Close the transport?
    transport, engine = await chess.engine.popen_uci("stockfish")

    # TODO: Configure through the API
    await engine.configure({"Threads": 4, "Hash": 1024})
    infiniteAnalysisTask = None

    await ws.send(json.dumps({
        'msg': 'connected'
    }))

    # TODO: stop infinite analysis to free resources
    while True:
        msg = await ws.recv()
        js = json.loads(msg)
        if js["msg"] == 'fen':
            board.set_fen(js["data"])

            if infiniteAnalysisTask:
                infiniteAnalysisTask.cancel()
            loop = asyncio.get_event_loop()
            infiniteAnalysisTask = loop.create_task(infiniteAnalysis(engine, board, ws))
        elif js["msg"] == 'pause':
            if infiniteAnalysisTask:
                infiniteAnalysisTask.cancel()
        elif js["msg"] == 'resume':
            if infiniteAnalysisTask.cancelled():
                loop = asyncio.get_event_loop()
                infiniteAnalysisTask = loop.create_task(infiniteAnalysis(engine, board, ws))

if __name__ == '__main__':

    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    server_cor = app.create_server(host="0.0.0.0", port=5000, return_asyncio_server=True, protocol=WebSocketProtocol)

    loop = asyncio.get_event_loop()
    task = loop.create_task(server_cor)
    server = loop.run_until_complete(task)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
    finally:
        # Wait for server to close
        close_task = server.close()
        loop.run_until_complete(close_task)

        # Complete all tasks on the loop
        for connection in server.connections:
            connection.close_if_idle()

