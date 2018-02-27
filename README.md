# wchatlog
微信聊天记录保存
## 目的
对于手机内存比较小的手机，微信的聊天记录也是挺占空间的，不过删了又挺可惜了，所以希望能够将消息保存到其他地方，这也是这个小程序的目的
## 使用
virtualenv --python=python3 venv  
source venv/bin/activate  
pip install -r requirements.txt  
python wchatlog.py

**注**: 如果要在后台运行，因为存在扫码登录的问题，所以先运行python wchatlog.py后等待扫码登录成功，
而后ctrl+c杀死该进程，这样就再运行nohup wchatlog.py &后就可以实现后台运行收集聊天日志信息了
