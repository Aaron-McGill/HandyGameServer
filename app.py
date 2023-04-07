from dataclasses import dataclass
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import json
from waitress import serve

db = SQLAlchemy()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"

db.init_app(app)

player_mappings = {}
game_ready_mappings = {}

@app.route('/games')
def get_games():
    game_type = request.args.get('type')
    active = request.args.get('active')
    query = db.session.query(Game)
    if game_type is not None and active is not None:
        games = query.filter(Game.type == game_type).filter(Game.active == (active == "true" or active == "True")).all()
    elif game_type is not None:
        games = query.filter(Game.type == game_type).all()
    elif active is not None:
        games = query.filter(Game.active == (active == "true" or active == "True")).all()
    else:
        games = query.all()
    return jsonify(games)

@app.route('/games', methods=['POST'])
def create_game():
    request_data = request.get_json()

    game_type = request_data['type']
    current_player = request_data['current_player']
    game = Game(
        type = game_type,
        board = generate_board_by_game_type(game_type),
        active = False,
        current_player = "1",
        players = {"1": current_player},
    )
    db.session.add(game)
    db.session.commit()

    # Add an entry to the cache to indicate the current player.
    player_mappings[game.id] = "1"

    # Add an entry to the cache to indicate the game is not ready.
    game_ready_mappings[game.id] = "false"

    return jsonify(game)

@app.route('/games/<int:game_id>')
def get_game(game_id):
    return jsonify(db.get_or_404(Game, game_id))

@app.route('/games/<int:game_id>/join', methods=['PUT'])
def join_game(game_id):
    request_data = request.get_json()
    current_player = request_data['current_player']

    game = db.get_or_404(Game, game_id)
    original_player_name = game.players["1"]
    game.players = {"1": original_player_name, "2": current_player}
    game.active = True

    db.session.flush()
    db.session.commit()

    # Update the cache to indicate the game is ready.
    game_ready_mappings[game_id] = "true"

    return jsonify(game)

@app.route('/games/<int:game_id>/makeMove', methods=['PUT'])
def make_move(game_id):
    request_data = request.get_json()
    updated_board = request_data['board']

    game = db.get_or_404(Game, game_id)
    current_player = game.current_player
    if current_player == "1":
        game.current_player = "2"
    else:
        game.current_player = "1"
    
    game.board = updated_board

    db.session.flush()
    db.session.commit()

    # Update the cache to indicate the current player has changed.
    player_mappings[game.id] = game.current_player
    
    return jsonify(game)

@app.route('/games/<int:game_id>/currentPlayer')
def get_current_player(game_id):
    return player_mappings[game_id]

@app.route('/games/<int:game_id>/gameReady')
def game_ready(game_id):
    return game_ready_mappings[game_id]

@app.route('/games/<int:game_id>', methods=['DELETE'])
def delete_game(game_id):
    db.session.query(Game).filter(Game.id == game_id).delete()
    db.session.commit()
    # Clear the entries from the cache
    player_mappings.pop(game_id)
    game_ready_mappings.pop(game_id)
    return ('', 204)

def generate_board_by_game_type(game_type):
    if game_type == 'tic-tac-toe':
        return [" " for i in range(9)]
    else: # Connect Four
        return [" " for i in range(16)]

@dataclass
class Game(db.Model):
    id: int
    type: str
    board: json
    active: bool
    current_player: str
    players: json

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String)
    board = db.Column(db.JSON)
    active = db.Column(db.Boolean, default=False)
    current_player = db.Column(db.String)
    players = db.Column(db.JSON)

if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
    serve(app, port=8080, host='0.0.0.0')