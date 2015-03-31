import logging
from django.conf import settings
logger = logging.getLogger(__name__)

def get_query_string(keyword, content_type, start, rows):
    
    logger.debug("Keyword %s" % keyword)
    logger.debug("Content type %s" % content_type)
   
    conjunction_parts = []
        
    # content
    if(keyword == '*'):
        logger.debug( "Skip wildcard condition: \""+keyword+"\"" )
    else:
        conjunction_parts.append("%s%%3A%s" % ('content', keyword))
    # contentType
    if not(len(content_type) == 1 and content_type[0] == "*"):
        disjunction_parts = []
        for ct in content_type:
            disjunction_parts.append("%s%%3A%s" % ('contentType', "%%22%s%%22" %ct))
        # contentType%3Aapplication\%2Fxml+OR+contentType%3Atext\%2Fplain
        disjunction_part = "(%s)" % ("+OR+".join(disjunction_parts))
        conjunction_parts.append(disjunction_part)
        
    # construct query part
    if(len(conjunction_parts) == 0):
        conjunctions = "*%3A*"
    else:
        conjunctions = "+AND+".join(conjunction_parts)
    
    
    limit = "start=%d&rows=%d" % (start,rows)
    
    query_part = conjunctions + "&" + limit
        
    query_string = settings.SERVER_SOLR_QUERY_URL.format(query_part)
    logger.info("Solr query string: %s" % query_string)
    return query_string