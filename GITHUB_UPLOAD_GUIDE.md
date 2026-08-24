# GitHub 업로드 안내

## 권장 업로드 순서

1. `OneGrip_Play_GitHub_업로드용_20260824.zip`의 압축을 푼다.
2. 압축 내부의 `OneGrip_Play/` 폴더에서 Git 저장소를 만든다.
3. `README.md`의 이미지와 상대경로 링크가 보이는지 확인한다.
4. 소스·문서·검증 결과를 기본 저장소에 올린다.
5. 조립 배포용 ZIP은 저장소에 반복해서 넣지 말고 GitHub Releases에 첨부한다.

```powershell
git init
git add .
git commit -m "Add OneGrip Play prototype design and validation files"
git branch -M main
git remote add origin <GitHub 저장소 주소>
git push -u origin main
```

## ZIP 구성 원칙

포함:

- 루트 `README.md`와 설계·부품 문서
- 현재 채택한 Full Module V3
- 검지·중지 8버튼 카세트 V2
- 3방향 손가락 입력 연구안
- RP2040·전원보드 서비스 카세트
- 팀원 최신안·Claude Code 최소 재현 원본
- 분석 스크립트와 검증 결과
- 전시 포스터 PPTX·PDF·PNG
- 제3자 출처와 라이선스 고지

제외:

- `.git/`
- `__pycache__/`, `.pyc`
- 포스터 백업·inspect 파일
- 전체 Desktop 체크포인트와 중간 캐시
- 중복된 구형 배포 ZIP
- 1 GB가 넘는 손 크기 실험용 중간 출력물

## 재현성 참고

`cad/onegrip-full-module-v3/build_full_module_blender.py`는 저장소 내부의
`cad/source_snapshot/team_claude_latest/`를 우선 사용한다. 원래 팀원 Desktop
작업 폴더가 없는 다른 컴퓨터에서도 필요한 상부 쉘·엄지·하부 짐벌 원본을 찾을
수 있도록 수정했다.

