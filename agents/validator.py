import json
from logger import proof_log
class Validator:
  @staticmethod
  def validate(txt):
    try:
      j=json.loads(txt)
      proof_log('Valid JSON produced')
      return j,True
    except Exception as e:
      proof_log('Invalid JSON detected')
      return str(e),False
