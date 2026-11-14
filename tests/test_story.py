from app.story import make_project
def test_scenes():
 p=make_project('A lost city',30,'16:9')
 assert len(p['scenes'])>=3 and p['language']=='English'
