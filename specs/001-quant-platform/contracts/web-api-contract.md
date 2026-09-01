# Web API Contract（FastAPI，`ashquant web` 启动）

Base: `http://127.0.0.1:8000`；全部 JSON；错误统一 `{"error": code, "message": str}`。

| 方法 | 路径 | 参数 | 返回 |
|---|---|---|---|
| GET | `/` | — | 单文件控制台页（静态 HTML） |
| GET | `/api/spot` | `?symbols=600519,300750` | `{quotes:[{symbol,name,price,pct_chg,change,timestamp,prev_close}]}` |
| GET | `/api/kline/{symbol}` | `?limit=800` | `{symbol, bars:[{date,open,high,low,close,volume}], ma:[{date,ma5,ma20,ma60}]}`（读缓存，无缓存时 404+提示先 fetch） |
| GET | `/api/predict/{symbol}` | — | `{symbol, direction, prob_up, confidence, signals:[{master,score,reason,quote,source}]}` 或 409（数据不足） |
| GET | `/api/paper` | — | `{cash, positions:[...], equity, trades_count}` |
| POST | `/api/paper/buy` | `{symbol, qty}` | `{ok, fill_price, fees, message}`；规则拒单 `{ok:false, reason}` 仍 200 |
| POST | `/api/paper/sell` | `{symbol, qty}` | 同上 |

页面行为（index.html 契约）：自选股输入→快照表 5 秒自动刷新；点行→右侧 K 线
（lightweight-charts，含 MA5/20/60 与成交量）；「预测」按钮→大师观点卡片；
底部固定免责声明与「不构成投资建议」。
