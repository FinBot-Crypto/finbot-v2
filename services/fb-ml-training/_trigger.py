import asyncio, nats, json
async def main():
    nc = await nats.connect('nats://crypto-nats:4222')
    js = nc.jetstream()
    SYMBOLS = [
        ('BTC/USDT','Major'),('ETH/USDT','Major'),
        ('SOL/USDT','Strong Alt'),('MATIC/USDT','Strong Alt'),('AVAX/USDT','Strong Alt'),
        ('LINK/USDT','Strong Alt'),('DOGE/USDT','Strong Alt'),('ADA/USDT','Strong Alt'),('XRP/USDT','Strong Alt'),
        ('ARB/USDT','High Volatility'),('OP/USDT','High Volatility'),('LDO/USDT','High Volatility'),
        ('ATOM/USDT','High Volatility'),('NEAR/USDT','High Volatility'),('INJ/USDT','High Volatility'),
        ('PEPE/USDT','High Volatility'),('SHIB/USDT','High Volatility'),('MEME/USDT','High Volatility'),('GALA/USDT','High Volatility')]
    assets = [{'symbol':s,'tier':t,'volume_24h':1e9,'last_price':0,'change_24h':0,'timestamp':''} for s,t in SYMBOLS]
    await js.publish('market.updated', json.dumps(assets).encode())
    print(f'PUBLICADO: {len(assets)} ativos em market.updated')
    await nc.close()
asyncio.run(main())
