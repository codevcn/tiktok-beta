# Huong dan setup chuan de chay project tren macOS

Tai lieu nay duoc viet theo dung hien trang cua repo va may Mac hien tai cua ban.
Muc tieu la setup theo huong on dinh, de chay duoc pipeline bang CPU tren macOS,
khong phu thuoc NVIDIA CUDA.

## 1. Tong quan nhanh

Project nay la mot pipeline Python de xu ly video theo chuoi:

1. Tai video bang `yt-dlp`
2. Xoa watermark bang `ffmpeg delogo` neu `links.json` co cau hinh watermark
3. Tach audio
4. Transcribe audio thanh file SRT bang `faster-whisper`
5. Sua typo trong SRT bang AI
6. Dich SRT bang AI neu chon flow co dich
7. Burn subtitle vao video bang `ffmpeg`

Tren macOS, huong chay dung va thuc te nhat la:

- Dung `CPU`, khong dung `GPU`
- Dung `Python 3.11`
- Dung ban `ffmpeg` co ho tro `libass`, `ass`, `subtitles`

## 2. Nhung diem can biet truoc khi setup

### 2.1. Khong nen dung `requirements.txt` nguyen ban tren macOS

File `requirements.txt` hien tai co cac goi CUDA:

- `nvidia-cublas-cu12`
- `nvidia-cuda-runtime-cu12`
- `nvidia-cudnn-cu12`
- `nvidia-cufft-cu12`

Day la nhom phu thuoc danh cho NVIDIA/CUDA, khong phu hop voi macOS.
Neu cai nguyen file nay, kha nang cao se loi hoac cai dat khong sach.

### 2.2. Khong nen dung Python 3.14 cho project nay

May cua ban hien dang co `python3` la `3.14.3`.
Voi nhom thu vien ML/audio nhu `faster-whisper`, dung Python moi nhat thuong de gap
van de wheel chua san sang day du.

Khuyen nghi chuan cho repo nay:

- Dung `Python 3.11`

### 2.3. Ban `ffmpeg` hien tai tren may ban chua du

May cua ban da co `ffmpeg`, nhung ban `ffmpeg` regular hien tai khong cho thay
filter `ass`/`subtitles`, trong khi code burn subtitle can den no.

Code hien tai burn sub bang:

```python
"-vf", f"ass='{ass_escaped}'"
```

Neu `ffmpeg` khong co `libass`, buoc burn subtitle se fail o cuoi pipeline.

Tren may cua ban con co mot tinh huong thuc te nua:

- `ffmpeg` regular hien dang la dependency cua `mpv` va `scrcpy`

Vi vay, `brew uninstall ffmpeg` co the bi Homebrew tu choi.
Huong khuyen nghi cho may cua ban la cai `ffmpeg-full` song song, roi uu tien PATH
cho no khi chay project, thay vi go bo `ffmpeg` regular ngay lap tuc.

### 2.4. Flow "khong dich thuat" van can AI

Flow 2 chi tat buoc dich, nhung van giu buoc sua typo SRT bang AI.
Vi vay, de chay het pipeline, ban van can it nhat mot API key hop le:

- `GOOGLE_API_KEY`, hoac
- `OPENAI_API_KEY`

## 3. Cai cac cong cu he thong bang Homebrew

Neu may chua co Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Kiem tra:

```bash
brew --version
```

## 4. Cai Python phu hop

### 4.1. Cai Python 3.11

```bash
brew install python@3.11
```

Kiem tra:

```bash
/opt/homebrew/bin/python3.11 -V
```

Ky vong:

```text
Python 3.11.x
```

Neu ban dung Mac Intel, duong dan co the la:

```bash
/usr/local/bin/python3.11 -V
```

### 4.2. Khong dung truc tiep `python3` neu no dang tro vao 3.14

De tranh nham lan, trong toan bo setup ben duoi hay uu tien goi truc tiep:

```bash
python3.11
```

hoac:

```bash
/opt/homebrew/bin/python3.11
```

## 5. Cai `ffmpeg` dung ban cho project

### 5.1. Vi sao khong dung ban `ffmpeg` regular

Ban Homebrew regular tren may ban co ghi chu:

- `ffmpeg-full includes additional tools and libraries that are not included in the regular ffmpeg formula.`

Project nay can burn ASS subtitle, vi vay ban nen dung `ffmpeg-full`.

### 5.2. Neu may da co `ffmpeg` regular

Kiem tra build hien tai:

```bash
ffmpeg -buildconf
ffmpeg -filters | grep -E " ass |subtitles|delogo"
```

Neu khong thay `ass` hoac `subtitles`, hay thay bang `ffmpeg-full`.

### 5.3. Cai `ffmpeg-full`

#### Cach khuyen nghi cho may cua ban: cai song song

May cua ban hien tai dang co `mpv` va `scrcpy` phu thuoc `ffmpeg`.
Vi vay, cach an toan nhat la khong go `ffmpeg` regular.

Hay cai them `ffmpeg-full`:

```bash
brew install ffmpeg-full
```

Sau do uu tien ban `ffmpeg-full` trong shell hien tai:

```bash
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"
hash -r
which ffmpeg
ffmpeg -buildconf
ffmpeg -filters | grep -E " ass |subtitles|delogo"
```

Neu `which ffmpeg` tra ve duong dan duoi `ffmpeg-full` va filter co `ass` hoac
`subtitles`, ban co the tiep tuc chay project.

Neu ban muon ap dung lau dai, co the them dong nay vao `~/.zshrc`:

```bash
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"
```

#### Cach thay the han `ffmpeg` regular

Chi dung cach nay neu ban chap nhan anh huong toi `mpv` va `scrcpy`.
Homebrew co the tu choi go `ffmpeg` vi dependency, nen neu van muon thay the han,
ban phai bo qua kiem tra dependency:

```bash
brew uninstall --ignore-dependencies ffmpeg
brew install ffmpeg-full
```

Neu may chua co `ffmpeg`:

```bash
brew install ffmpeg-full
```

Kiem tra sau khi cai:

```bash
which ffmpeg
ffmpeg -buildconf
ffmpeg -filters | grep -E " ass |subtitles|delogo"
```

Ban can thay toi thieu:

- `delogo`
- `ass` hoac `subtitles`

Neu van khong thay `ass`/`subtitles`, dung lai o day va xu ly xong `ffmpeg`
truoc khi chay project. Neu bo qua buoc nay, pipeline se loi o buoc burn subtitle.

### 5.4. Neu may bao `zsh: command not found: rg`

Tai lieu nay da uu tien dung `grep` de khong phu thuoc `ripgrep`.
Neu ban thich dung `rg`, co the cai them:

```bash
brew install ripgrep
```

Sau do co the doi cac lenh `grep -E` thanh `rg` neu muon.

## 6. Cai `yt-dlp`

```bash
brew install yt-dlp
```

Kiem tra:

```bash
yt-dlp --version
```

## 7. Tao moi truong ao Python

Di chuyen vao repo:

```bash
cd /Users/buiquanghuy/Documents/lthloi/tiktok-beta
```

Tao venv:

```bash
python3.11 -m venv .venv
```

Kich hoat:

```bash
source .venv/bin/activate
```

Nang cap cong cu cai dat:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Luu y:

- File `venv.cmd` va `dev.cmd` trong repo la danh cho Windows
- Tren macOS, ban khong dung cac file `.cmd`

## 8. Cai Python dependencies theo cach an toan cho macOS

Khong cai bang `pip install -r requirements.txt`.

Hay cai nhom goi phu hop voi CPU/macOS:

```bash
pip install pysubs2 google-genai faster-whisper yt-dlp openai
```

Neu ban muon giu lai danh sach goi cho de copy, day la nhom toi thieu:

- `pysubs2`
- `google-genai`
- `faster-whisper`
- `yt-dlp`
- `openai`

### 8.1. Kiem tra import ngay sau khi cai

```bash
python -c "import pysubs2, google.genai, faster_whisper, openai; print('python_deps_ok')"
```

Neu lenh nay in ra:

```text
python_deps_ok
```

thi phan dependency Python da on.

## 9. Tao file `.env`

Project doc `.env` thu cong, vi vay ban can tao file o thu muc goc cua repo:

```bash
touch .env
```

Noi dung goi y:

```env
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

Ban co the chi dung 1 key, nhung khuyen nghi:

- Co `GOOGLE_API_KEY` de dung tier uu tien
- Co them `OPENAI_API_KEY` de lam fallback

Luu y:

- Neu khong co ca 2 key, buoc sua typo bang AI se that bai
- Flow 2 van can AI, vi no chi bo qua buoc dich, khong bo qua buoc sua typo

## 10. Kiem tra `links.json` truoc khi chay

File cau hinh hien tai nam o:

```text
data/video/input/links.json
```

Co vai diem ban nen kiem tra:

### 10.1. `use-gpu`

Tren macOS, de:

```json
"use-gpu": false
```

Khong bat `true`, vi code GPU hien tai duoc thiet ke cho CUDA/NVIDIA.

### 10.2. `link`

Dam bao link video co the tai duoc bang `yt-dlp`.

### 10.3. `original-lang-code`

Co the de nhu hien tai neu ban biet ngon nguon goc.
Vi du:

```json
"original-lang-code": "ja"
```

### 10.4. `target-lang-code`

Neu chay flow co dich, ngon ngu dich nen khac ngon ngu goc.
Hien tai file cua ban dang de:

```json
"target-lang-code": "ja"
```

Nghia la buoc dich se dich sang tieng Nhat, trong khi `original-lang-code` cung la `ja`.
Neu muc tieu cua ban la dich sang tieng Viet, hay doi thanh:

```json
"target-lang-code": "vi"
```

### 10.5. `watermark`

Neu toa do watermark sai, buoc `delogo` co the cho ket qua xau hoac loi.
Neu video khong can xoa watermark, ban co the bo field `watermark`.

## 11. Smoke test truoc khi chay that

Sau khi kich hoat venv, chay lan luot:

```bash
python -c "import pysubs2, google.genai, faster_whisper, openai; print('deps_ok')"
python -c "import sys; sys.path.insert(0, 'src'); import main; print('entry_import_ok')"
ffmpeg -filters | grep -E " ass |subtitles|delogo"
yt-dlp --version
```

Neu moi thu on, ban se ky vong:

- `deps_ok`
- `entry_import_ok`
- `ffmpeg` co `delogo`
- `ffmpeg` co `ass` hoac `subtitles`
- `yt-dlp` in ra version

## 12. Cach chay project tren macOS

Sau khi kich hoat venv:

```bash
cd /Users/buiquanghuy/Documents/lthloi/tiktok-beta
source .venv/bin/activate
python src/main.py
```

Luu y:

- Khong dung `python "src\main.py"` vi do la kieu path Windows
- Tren macOS dung `python src/main.py`

Khi menu hien ra:

- Chon `1` neu muon vua sua typo vua dich vua burn sub
- Chon `2` neu muon sua typo va burn sub, khong dich

## 13. Nhung loi thuong gap va cach xu ly

### 13.1. `ModuleNotFoundError: No module named 'pysubs2'`

Nguyen nhan:

- Chua cai dependency
- Chua kich hoat `.venv`

Xu ly:

```bash
source .venv/bin/activate
pip install pysubs2 google-genai faster-whisper yt-dlp openai
```

### 13.2. `ffmpeg` khong co `ass` hoac `subtitles`

Nguyen nhan:

- Dang dung ban `ffmpeg` regular

Xu ly uu tien:

```bash
brew install ffmpeg-full
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"
hash -r
which ffmpeg
ffmpeg -filters | grep -E " ass |subtitles|delogo"
```

Neu Homebrew bao khong cho `brew uninstall ffmpeg` vi `mpv` hoac `scrcpy`, do la
hanh vi binh thuong. Khong can go `ffmpeg` regular de tiep tuc setup project.

Chi khi ban muon thay the han moi can dung:

```bash
brew uninstall --ignore-dependencies ffmpeg
brew install ffmpeg-full
```

### 13.3. Loi o buoc AI

Nguyen nhan thuong gap:

- Thieu `GOOGLE_API_KEY`
- Thieu `OPENAI_API_KEY`
- API key sai
- Het quota hoac bi rate limit

Xu ly:

- Kiem tra file `.env`
- Kiem tra key con hieu luc
- Neu co, dien ca 2 key de co fallback

### 13.4. Loi do `faster-whisper`

Nguyen nhan thuong gap:

- Dung Python qua moi
- Moi truong ao tao sai interpreter

Xu ly:

```bash
deactivate
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install pysubs2 google-genai faster-whisper yt-dlp openai
```

### 13.5. Chay rat cham

Dieu nay binh thuong tren macOS khi project dang chay CPU path.
Buoc transcribe voi model `large-v3` co the ton kha nhieu thoi gian, nhat la lan dau
vi con co the phai tai model.

## 14. Checklist setup ngan gon

Neu ban muon mot checklist thuc thi nhanh, dung dung thu tu nay:

```bash
brew install python@3.11
brew install yt-dlp
brew install ffmpeg-full
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"
hash -r
cd /Users/buiquanghuy/Documents/lthloi/tiktok-beta
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install pysubs2 google-genai faster-whisper yt-dlp openai
python -c "import pysubs2, google.genai, faster_whisper, openai; print('deps_ok')"
python -c "import sys; sys.path.insert(0, 'src'); import main; print('entry_import_ok')"
ffmpeg -filters | grep -E " ass |subtitles|delogo"
python src/main.py
```

## 15. Trang thai setup toi khuyen nghi cho may cua ban

Trang thai muc tieu de duoc xem la "setup dung":

- `python3.11` dung de tao `.venv`
- `.venv` da duoc kich hoat
- Import duoc `pysubs2`, `google.genai`, `faster_whisper`, `openai`
- Shell dang uu tien `ffmpeg-full` neu may co song song nhieu ban `ffmpeg`
- `ffmpeg` co `delogo`
- `ffmpeg` co `ass` hoac `subtitles`
- `yt-dlp` chay duoc
- `.env` co API key hop le
- `data/video/input/links.json` de `"use-gpu": false`
- Chay duoc `python src/main.py`

Neu tat ca cac muc tren deu dung, project nay co kha nang cao se chay duoc tren macOS
theo huong CPU.
