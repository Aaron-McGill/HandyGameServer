from dataclasses import dataclass
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"

db.init_app(app)

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
        current_player = current_player,
        players = [current_player],
    )
    db.session.add(game)
    db.session.commit()

    return jsonify(game)

@app.route('/games/<int:game_id>')
def get_game(game_id):
    return jsonify(db.get_or_404(Game, game_id))

@app.route('/games/<int:game_id>/join', methods=['PUT'])
def join_game(game_id):
    request_data = request.get_json()
    current_player = request_data['current_player']

    game = db.get_or_404(Game, game_id)
    game.players = [game.current_player, current_player]
    game.active = True

    db.session.flush()
    db.session.commit()

    return jsonify(game)

@app.route('/games/<int:game_id>/makeMove', methods=['PUT'])
def make_move(game_id):
    request_data = request.get_json()
    updated_board = request_data['board']

    game = db.get_or_404(Game, game_id)
    current_player = game.current_player
    for player in game.players:
        if current_player != player:
            game.current_player = player
    
    game.board = updated_board

    db.session.flush()
    db.session.commit()
    
    return jsonify(game)

@app.route('/games/<int:game_id>', methods=['DELETE'])
def delete_game(game_id):
    db.session.query(Game).filter(Game.id == game_id).delete()
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
    app.run(host='0.0.0.0', port=8080)