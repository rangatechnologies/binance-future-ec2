import websocket,json
from BinanceFutures_Custom import Client, MarketData
from config import API_TEST_SECRET,API_TEST_KEY, long_entry_per,long_tp_per,short_entry_per,short_tp_per
import math
from tinydb import TinyDB, Query
db = TinyDB('db.json')

# @@@@@@@@@@@@@@@--------Create a client-----------@@@@@@@@@@@@@@@@
# Create client
client = Client(API_TEST_KEY, API_TEST_SECRET, testnet=True)
stepSize = 0.01
symbol = 'BTCUSDT'
def on_message(ws, message):
    # Parse the JSON message
    json_message = json.loads(message)
    # print(f"response = {json_message}")
    data = json_message['data']
    kline=data['k']
    open = float(kline['o'])
    close = float(kline['c'])
    high = float(kline['h'])
    low = float(kline['l'])
    # Is this kline closed?
    kline_close= kline['x']
    print(f"open = {open}, close = {close}, high = {high}, low = {low}, is line close = {kline_close} ")


    #@@@@@@@@@@@@@@@@@@@@@@@_--------------DB managing-----------@@@@@@@@@@@@@@@@@@@@@
    # db.insert({'close': str(close), 'kline_close': str(kline_close)})
    # db.insert({'name': 'db', 'close': 30, 'kline_close': 'false'})
    User = Query()
    data = db.search(User.name == 'db')
    close_pre = float(data[0]['close'])
    print(close_pre)

    # create a Query instance to find the data you want to update
    User = Query()
    user_to_update = User.name == 'db'
    db.update({'close': str(close),'kline_close':str(kline_close) }, user_to_update)

    # Calculate order prices
    # Long entry
    long_entry_price = round(open * (1 + long_entry_per/100),1)
    # Long TP
    long_tp_price    = round(open * (1 + long_tp_per/100),1)
    # Short entry
    short_entry_price = round(open * (1 - short_entry_per/100),1)
    # Short TP
    short_tp_price    = round(open * (1 - short_tp_per/100),1)
    print(f"Order Prices long_entry_price = {long_entry_price}, long_tp = {long_tp_price}, short_entry_price = {short_entry_price}, short_tp= {short_tp_price}")
    # @@@@@@@@@@@@@@@@@@@----------Calculate Account Balance--------@@@@@@@@@@@@@@@@
    # Calculate order size by percentage parameter
    balance = client.balance()
    # print(f"balance = {balance}")
    quoteAsset_balance = 0.0
    try:
        for coin in balance:
            if coin['asset'] == "USDT":
                quoteAsset_balance = coin['balance']
                print(f"==> {coin['asset']} have quoteAsset Balance = {quoteAsset_balance}")
        quoteAsset_balance = float(quoteAsset_balance) * 0.1
        print(f"QuoteAsset Balance = {quoteAsset_balance}")
        order_qty = quoteAsset_balance / close
        precision = int(round(-math.log(float(stepSize), 10), 0))
        quantity = float(round(float(order_qty), precision))
    except Exception as e:
        print(f"Balance format = {e}")

    #@@@@@@@@@@@@@@@@@@@------------Position Sizes-----------------@@@@@@@@@@@@@@@@@
    position_info = client.position_info(symbol=symbol)
    position_quantity_short = 0
    position_quantity_long = 0
    for pos in position_info:
        if pos['positionSide'] == "SHORT":
            position_quantity_short = pos["positionAmt"]
            position_quantity_short = abs(float(position_quantity_short))
        if pos['positionSide'] == "LONG":
            position_quantity_long = pos["positionAmt"]
            position_quantity_long = abs(float(position_quantity_long))
    print(f"===> Positions long = {position_quantity_long} = {position_quantity_long == 0.0}, Positions short = {position_quantity_short}= {position_quantity_short == 0.0}")


    # Activate trading

    #@@@@@@@@@@@@@@@@@@@@--------------Order conditions--------------@@@@@@@@@@@@@@@@

    if close >= long_entry_price and close_pre< long_entry_price and position_quantity_long == 0.0 and position_quantity_short==0.0:

        # Open long entry
        cancel_open_order_resp = client.cancel_all_open_orders(symbol=symbol)
        try:

            print("==> Long entry order")
            response_open = client.new_order(side="BUY",
                                             symbol=symbol,
                                             quantity=quantity,
                                             orderType="MARKET",
                                             # price = long_entry_price,
                                             positionSide="LONG"
                                             # timeInForce="GTC"
                                             )
            print(f"Long entry response = {response_open}")

        except Exception as e:
            print(f"Long entry error = {e}")
        # TP
        try:
            # TP 01 Order
            response_TP_01 = client.new_order(side="SELL",
                                              symbol=symbol,
                                              quantity=quantity,
                                              orderType="TAKE_PROFIT_MARKET",
                                              positionSide="LONG",
                                              timeInForce="GTC",
                                              stopPrice=long_tp_price
                                              )
            print(f"Long TP response = {response_TP_01}")
        except Exception as e:
            print(f"Long TP error = {e}")

    if close <= short_entry_price and close_pre> short_entry_price and position_quantity_long == 0 and position_quantity_short==0:
        # Open short position
        # Open long entry
        cancel_open_order_resp = client.cancel_all_open_orders(symbol=symbol)
        print("==> Short entry order")
        response_open = client.new_order(side="SELL",
                                         symbol=symbol,
                                         quantity=quantity,
                                         orderType="MARKET",
                                         # price=short_entry_price,
                                         positionSide="SHORT",
                                         # timeInForce="GTC"
                                         )
        print(f"Short entry response = {response_open}")

        # TP
        try:
            # TP 01 Order
            response_TP_01 = client.new_order(side="BUY",
                                              symbol=symbol,
                                              quantity=quantity,
                                              orderType="TAKE_PROFIT_MARKET",
                                              positionSide="SHORT",
                                              timeInForce="GTC",
                                              stopPrice=short_tp_price
                                              )
            print(f"Short TP response = {response_TP_01}")
        except Exception as e:
            print(f"Short TP error = {e}")


    # if close < open * (1 + 0.20/100) and close> open * (1 - 0.20/100):
    #     # Cancel all open orders
    #


def on_open(ws):
    print("Opened connection")
def on_error(ws, error):
  print(error)
def on_close(ws, close_status_code, close_msg):
    print("### closed ###")
def streamKline(currency, interval):
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(f"wss://fstream.binance.com/stream?streams={currency}@kline_{interval}", on_open=on_open,
                                on_message=on_message, on_close=on_close, on_error=on_error)
    ws.run_forever()

streamKline('btcusdt', '1m')


