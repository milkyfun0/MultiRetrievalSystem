cd ./algorithm
python launcher/run_all.py

cd ./backend
uvicorn app.main:app --reload

cd ./frontend
npm run build
npm run dev

cd ./backend
set MMR_PUBLIC_BASE_URL=http://10.98.229.114:8000
uvicorn app.main:app --host 0.0.0.0 --port 8000


 cd deploy/nginx
 .\nginx.exe -c conf/nginx.conf
 .\nginx.exe -s stop
http://10.98.229.114:5174/



F:\Code\MultiRetrievalSystem\data\Video

F:\Code\MultiRetrievalSystem\data\Meidical

F:\Code\MultiRetrievalSystem\data\Image

F:\Code\MultiRetrievalSystem\data\LongVIdeo.mp4








