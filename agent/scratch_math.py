import pandas as pd

# Assume fast backtest output
# 15532 trades total over 6 symbols
# 464.43% sum of returns

# Let's model a portfolio starting at $100,000, 20% risk per trade.
capital = 100000
risk_per_trade = 0.20
slippage = 0.0001
commission = 0.005

# In fast backtest: Total Theoretical Return: 464.43% (sum of returns across 6 symbols)
# Average return per symbol = 464.43 / 6 = 77.405%

# If we allocate 20% to each symbol and it grew by 77.405%:
gross_profit = capital * risk_per_trade * 6 * (0.77405) # = $92,886
trades = 15532

# Average share price ~ $200
avg_shares_per_trade = (capital * risk_per_trade) / 200 # = 100 shares
total_commissions = trades * avg_shares_per_trade * commission # = $7,766
total_slippage = trades * (capital * risk_per_trade) * slippage # = $31,064

net_profit = gross_profit - total_commissions - total_slippage
end_capital = capital + net_profit

print(f"Gross Profit: ${gross_profit:,.2f}")
print(f"Commissions: ${total_commissions:,.2f}")
print(f"Slippage: ${total_slippage:,.2f}")
print(f"Net Profit: ${net_profit:,.2f}")
print(f"End Capital: ${end_capital:,.2f}")
