git log -1 --pretty=%%h_(%%ad) > version.txt
echo|set /p="Built with PyInstaller: " >> version.txt
date /t >> version.txt

pyinstaller --noconfirm --clean -D SabView.py

rem YUCK! Need to copy in ffmpeg stuff
rem TODO: Get appropriate directory from Windows path "where" etc
copy c:\users\vimal\anaconda3\envs\torsion\Library\bin\ff*.exe dist\SabView
copy c:\users\vimal\anaconda3\envs\torsion\Library\bin\av*.dll dist\SabView
copy c:\users\vimal\anaconda3\envs\torsion\Library\bin\postproc-55.dll  dist\SabView
copy c:\users\vimal\anaconda3\envs\torsion\Library\bin\swscale-5.dll dist\SabView
copy c:\users\vimal\anaconda3\envs\torsion\Library\bin\swresample-3.dll dist\SabView