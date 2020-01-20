from flask import Flask
import chess
import chess.engine

app = Flask(__name__)


@app.route('/<path:fen>')
def hello_world(fen):
  engine = chess.engine.SimpleEngine.popen_uci("stockfish")
  board = chess.Board()
  board.set_fen(fen)
  engine.configure({"Threads": 16})
  info = engine.analyse(board, chess.engine.Limit(time=5))
  return board.variation_san(info.pv)

if __name__ == '__main__':
  app.run()