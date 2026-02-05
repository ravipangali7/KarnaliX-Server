"""
Game-related serializers for KarnaliX.
"""
from rest_framework import serializers
from core.models import GameProvider, Game, Bet, GameTransactionLog


class GameProviderSerializer(serializers.ModelSerializer):
    """Serializer for game providers."""
    games_count = serializers.SerializerMethodField()
    
    class Meta:
        model = GameProvider
        fields = ['id', 'name', 'code', 'api_endpoint', 'status', 'games_count', 'created_at']
    
    def get_games_count(self, obj):
        return obj.games.count()


class GameProviderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating game providers."""
    class Meta:
        model = GameProvider
        fields = ['name', 'code', 'api_endpoint', 'api_secret', 'api_token', 'status']


class GameSerializer(serializers.ModelSerializer):
    """Serializer for games."""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    
    class Meta:
        model = Game
        fields = [
            'id', 'provider', 'provider_name', 'name', 'game_type',
            'min_bet', 'max_bet', 'rtp', 'status', 'created_at'
        ]


class GameCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating games."""
    class Meta:
        model = Game
        fields = ['provider', 'name', 'provider_game_uid', 'game_type', 'min_bet', 'max_bet', 'rtp', 'status']


class BetSerializer(serializers.ModelSerializer):
    """Serializer for bets."""
    username = serializers.CharField(source='user.username', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True)
    provider_name = serializers.CharField(source='game.provider.name', read_only=True)
    
    class Meta:
        model = Bet
        fields = [
            'id', 'user', 'username', 'game', 'game_name', 'provider_name',
            'provider_bet_id', 'bet_amount', 'odds', 'possible_win',
            'result', 'win_amount', 'placed_at', 'settled_at'
        ]


class BetCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bets."""
    class Meta:
        model = Bet
        fields = ['game', 'bet_amount', 'odds']


class GameTransactionLogSerializer(serializers.ModelSerializer):
    """Serializer for game transaction logs."""
    username = serializers.CharField(source='user.username', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    
    class Meta:
        model = GameTransactionLog
        fields = [
            'id', 'user', 'username', 'game', 'game_name',
            'provider', 'provider_name', 'provider_transaction_id',
            'provider_bet_id', 'transaction_type', 'round', 'match',
            'bet_amount', 'win_amount', 'before_balance', 'after_balance',
            'status', 'created_at', 'processed_at'
        ]


class ProfitLossSerializer(serializers.Serializer):
    """Serializer for profit/loss reports."""
    total_bets = serializers.IntegerField()
    total_bet_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_win_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_loss = serializers.DecimalField(max_digits=15, decimal_places=2)


class TopWinnerSerializer(serializers.Serializer):
    """Serializer for top winners."""
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    total_win = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_bet = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2)
