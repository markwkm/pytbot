import logging

# Configure logging facility
logger = logging.getLogger('pytbot')
hdlr = logging.FileHandler('pytbot.log')
formatter = logging.Formatter('%(asctime)s:%(name)s[%(process)d] %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

