#!/usr/bin/env python
#############################################################################
##
## This file is part of Taurus
## 
## http://taurus-scada.org
##
## Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
## 
## Taurus is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
## 
## Taurus is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
## 
## You should have received a copy of the GNU Lesser General Public License
## along with Taurus.  If not, see <http://www.gnu.org/licenses/>.
##
#############################################################################

__all__ = ['EvaluationDeviceNameValidator',
           'EvaluationAttributeNameValidator']

import re
import hashlib

from taurus import isValidName, debug
from taurus.core import TaurusElementType

from taurus.core.taurusvalidator import (TaurusAttributeNameValidator, 
                                         TaurusDeviceNameValidator, 
                                         TaurusAuthorityNameValidator)

# Pattern for python variables
PY_VAR = r'(?<![\.a-zA-Z0-9_])[a-zA-Z_][a-zA-Z0-9_]*'
PY_VAR_RE = re.compile(PY_VAR)
# Pattern for semicolon-separated <variable>=<value> pairs (in URI paths)
K_EQUALS_V = r'(%s)=([^?#=;]+)' % PY_VAR
K_EQUALS_V_RE = re.compile(K_EQUALS_V)
# 
QUOTED_TEXT = '(".*?"|\'.*?\')'
QUOTED_TEXT_RE = re.compile(QUOTED_TEXT)


def _findAllTokensBetweenChars(string, start, end, n=None):
    '''Finds the text between (possibly nested) delimiters in a string.
    In case of nested delimiters, only the outermost level is 
    returned.
    
    Example:: 
      
      _findAllTokensBetweenChars('{foo}bar{zig{zag}}boom', '{', '}') 
      --> ['foo', 'zig{zag}']
    

    :param string: (str) the expression to parse
    :param start: (str) the char delimiting the start of a token
    :param end: (str) the char delimiting the end of a token
    :param n: (int or None) If an int is passed, it sets the maximum number 
              of tokens to be found
    
    :return: (list<str>) a list of refs (not including the brackets)
    '''
    if start == end:
        raise ValueError('star_char must be different from end_char')
    if string.count(start) != string.count(end):
        raise ValueError('Non-matching delimiters (%i "%s" vs %i "%s")' % 
                         string.count(start), start, string.count(end), end)
    tokens = []
    rest = string
    while len(tokens) != n:
        s = rest.find(start)
        if s < 0:
            return tokens
        e = rest.find(end)+1
        while rest[s:e].count(start) != rest[s:e].count(end):
            ne = rest[e:].find(end)
            e = e + 1 + ne
        tokens.append(rest[s+1:e-1])
        rest = rest[e:]
    return tokens


class EvaluationAuthorityNameValidator(TaurusAuthorityNameValidator):
    '''Validator for Evaluation authority names. For now, the only supported 
    authority (in strict mode) is "//localhost":
    '''
    scheme = 'eval'
    authority = '//localhost'
    path = '(?!)'
    query = '(?!)'
    fragment = '(?!)'

    @property
    def nonStrictNamePattern(self):
        '''implement in derived classes if a "less strict" pattern is allowed
        (e.g. for backwards-compatibility, "tango://a/b/c" could be an accepted 
        device name, even if it breaks RFC3986).
        '''
        return r'^(?P<scheme>eval|evaluation)://(db=(?P<dbname>[^?#;]+))$'


class EvaluationDeviceNameValidator(TaurusDeviceNameValidator):    
    '''Validator for Evaluation device names. Apart from the standard named 
    groups (scheme, authority, path, query and fragment), the following named 
    groups are created:
    
     - devname: device name (either _evalname or _evalclass)
     - [_evalname]: evaluation instance name (aka non-dotted dev name) 
     - [_evalclass]: evaluator class name (if dotted name given)
     - [_old_devname]: devname without "@". Only in non-strict mode
     - [_dbname] and [_subst]: unused. Only if non-strict mode
     
    Note: brackets on the group name indicate that this group will only contain
    a string if the URI contains it.
    '''

    scheme = 'eval'
    authority = EvaluationAuthorityNameValidator.authority
    _evaluatorname = r'((?P<_evalname>[^/?#:\.=]+)|(?P<_evalclass>(\w+\.)+\w+))'
    devname = r'(?P<devname>@%s)' % _evaluatorname
    path = r'(?!//)/?%s' % devname
    query = '(?!)'
    fragment = '(?!)' 
    
    def getUriGroups(self, name, strict=None):
        '''reimplemented from :class:`TaurusDeviceNameValidator` to provide 
        backwards compatibility with ol syntax'''
        groups = TaurusDeviceNameValidator.getUriGroups(self, name, 
                                                        strict=strict)
        if groups is not None and not groups['__STRICT__']:
            _old_devname = groups['_old_devname']
            groups['devname'] = '@%s' % _old_devname
            if '.' in _old_devname:
                groups['_evalname'] = None
                groups['_evalclass'] = _old_devname
            else:
                groups['_evalname'] = _old_devname
                groups['_evalclass'] = None
        return groups

    
    def getNames(self, fullname, factory=None):
        '''reimplemented from :class:`TaurusDeviceNameValidator`'''
        from evalfactory import EvaluationFactory
        #TODO: add mechanism to select strict mode instead of hardcoding here
        groups = self.getUriGroups(fullname)
        if groups is None:
            return None      

        authority = groups.get('authority')
        if authority is None:
            f_or_fklass = factory or EvaluationFactory
            groups['authority'] = authority = f_or_fklass.DEFAULT_AUTHORITY
        
        complete = 'eval:%(authority)s/%(devname)s' % groups
        normal = '%(devname)s' % groups
        short = normal.lstrip('@')

        return complete, normal, short  
            
    @property
    def nonStrictNamePattern(self):
        '''In non-strict mode support old-style eval names
        '''
        p = r'^(?P<scheme>eval|evaluation)://(db=(?P<_dbname>[^?#;]+);)?' + \
            r'(dev=(?P<_old_devname>%s))' % self._evaluatorname + \
            r'(\?(?!configuration=)(?P<_subst>[^#?]*))?$'
        return p


class EvaluationAttributeNameValidator(TaurusAttributeNameValidator):
    '''Validator for Evaluation attribute names. Apart from the standard named 
    groups (scheme, authority, path, query and fragment), the following named 
    groups are created:
    
     - attrname: attribute name. same as concatenating _subst with _expr 
     - _expr: a mathematical expression
     - [_subst]: a semicolon-separated repetition of key=value (for replacing 
       them in _expr) 
     - [devname]: as in :class:`EvaluationDeviceNameValidator`
     - [_evalname]: evaluation instance name (aka non-dotted dev name) 
     - [_evalclass]: evaluator class name (if dotted name given)
     - [_old_devname]: devname without "@". Only in non-strict mode
     - [_dbname] and [_subst]: unused. Only if non-strict mode
     
     
    Note: brackets on the group name indicate that this group will only contain
    a string if the URI contains it.
    '''
    scheme = 'eval'
    authority = EvaluationAuthorityNameValidator.authority
    path = ((r'(?!//)/?(%s/)?' + 
             r'(?P<attrname>(?P<_subst>(%s;)*)(?P<_expr>[^?#]+))') % 
            (EvaluationDeviceNameValidator.devname, K_EQUALS_V)
            )
    query = '(?!)'
    fragment = '(?P<cfgkey>[^# ]*)'
    
    @staticmethod
    def expandExpr(expr, substmap):
        '''expands expr by substituting all keys in map by their value.
        Note that eval references in expr (i.e. text within curly brackets) 
        is not substituted.
        
        :param expr: (str) string that may contain symbols defined in symbolMap
        :param symbolMap: (dict or str) dictionary whose keys (strings) are 
                          symbols to be substituted in `expr` and whose values 
                          are the corresponding replacements. Alternatively, a 
                          string containing a semi-colon separated list of 
                          symbol=value pairs can also be passed.
        '''
        if isinstance(substmap, str):
            substmap = dict(K_EQUALS_V_RE.findall(substmap))
        ret = expr
        protected = {}
        
        # temporarily replace the text within quotes by hash-based placeholders 
        for s in QUOTED_TEXT_RE.findall(expr):
            placeholder = hashlib.md5(s).hexdigest() 
            protected[placeholder] = s
            ret = re.sub(s, placeholder, ret)
                
        # Substitute each k by its v in the expr (unless they are in references) 
        for k,v in substmap.iteritems():
            # create a pattern for matching complete word k 
            # unless it is within between curly brackets
            keyPattern = r'(?<!\w)%s(?!\w)(?![^\{]*\})'% k
            # substitute matches of keyPattern by their value 
            ret = re.sub(keyPattern, v, ret)
        
        #restore the protected strings
        for placeholder,s in protected.iteritems():
            ret = re.sub(placeholder, s, ret)
        return ret
    
    @staticmethod
    def getRefs(expr):
        '''Find the attribute references (strings within brackets) in an eval 
        expression. In case of nested references, only the outermost level is 
        returned.
        
        Example: val.findRefs('{foo}bar{zig{zag}}boom') --> ['foo', 'zig{zag}']
            
        :param expr: (str) the expression to parse
        
        :return (list<str>) a list of refs (not including the brackets)
        '''
        return _findAllTokensBetweenChars(expr, '{', '}')
            
    def isValid(self, name, matchLevel=None, strict=None):
        '''reimplemented from :class:`TaurusAttributeNameValidator` to do extra
        check on references validity (recursive) 
        '''
        # Standard implementation 
        if matchLevel is not None:
            groups = self._isValidAtLevel(name, matchLevel=matchLevel)
        else:
            groups = self.getUriGroups(name, strict=strict)
        if groups is None:
            return False
        
        #now find the references (they can be in expr and in subst)
        _expr = groups['_expr']
        _subst = groups['_subst'] or ''
        for s in (_expr, _subst):
            for ref in self.getRefs(s):
                if not isValidName(ref, etypes=(TaurusElementType.Attribute,), 
                                   strict=strict):
                    debug('"%s" is invalid because ref "%s" is not a ' + \
                            'valid attribute', name, ref)
                    return False
        return True

    def getUriGroups(self, name, strict=None):
        '''reimplemented from :class:`TaurusAttributeNameValidator` to provide 
        backwards compatibility with old syntax'''
        groups = TaurusAttributeNameValidator.getUriGroups(self, name, 
                                                           strict=strict)
        if groups is None:
            return None
        
        if not groups['__STRICT__']:
            #adapt attrname to what would be in strict mode
            _subst = groups['_subst'] or ''
            _expr = groups['_expr']
            if _subst:
                groups['attrname'] = "%s;%s" % (_subst.rstrip(';'), _expr)
            else:
                groups['attrname'] = _expr
                
            # adapt devname to what would be in strict mode
            old_devname = groups['_old_devname']
            if old_devname is None:
                groups['devname'] = None
            else:
                groups['devname'] = '@%s' % old_devname
                
        # check that there are not ";" in the expr (ign. quoted text and refs)
        sanitized_expr = QUOTED_TEXT_RE.sub('', groups['_expr'])
        for ref in self.getRefs(sanitized_expr):
            sanitized_expr = sanitized_expr.replace(ref, '')
        if ";" in sanitized_expr:
            return None
        
        return groups
    
    def getNames(self, fullname, factory=None, cfgkey=False):
        '''reimplemented from :class:`TaurusDeviceNameValidator`'''
        from evalfactory import EvaluationFactory
        groups = self.getUriGroups(fullname) 
        if groups is None:
            return None
        
        f_or_fklass = factory or EvaluationFactory

        authority = groups.get('authority')
        if authority is None:
            groups['authority'] = authority = f_or_fklass.DEFAULT_AUTHORITY
        
        devname = groups.get('devname')
        if devname is None:
            groups['devname'] = devname = f_or_fklass.DEFAULT_DEVICE
        
        expandedAttr = self.getExpandedExpr(fullname)
        
        complete = 'eval:%s/%s/%s' % (authority, devname, expandedAttr)
        normal = groups['attrname']
        if devname != f_or_fklass.DEFAULT_DEVICE:
            normal = '%s/%s' % (devname, normal)
        if authority != f_or_fklass.DEFAULT_AUTHORITY:
            normal = '%s/%s' % (authority, normal) 
        short = groups['_expr']

        # return fragment if cfgkey
        if cfgkey:
            key = groups.get('cfgkey', None)
            return complete, normal, short, key
        return complete, normal, short

    @property
    def nonStrictNamePattern(self):
        '''In non-strict mode support old-style eval config names
        '''
        p = r'^(?P<scheme>eval|evaluation)://(db=(?P<_dbname>[^?#;]+);)?' + \
            r'(dev=(?P<_old_devname>[^?#;]+);)?' + \
            r'(?P<_expr>[^?#;]+)' + \
            r'(?P<_substquery>\?(?!configuration=)(?P<_subst>[^#?]*))?' + \
            r'(\?(?P<query>configuration=?(?P<cfgkey>[^#?]*)))?$'
        return p
    
    def getExpandedExpr(self, name):
        '''
        Returns the expanded expression from the attribute name URI
        
        :param name: (str) eval attribute URI
        
        :return: (str) the expression (from the name )expanded with any 
                 substitution k,v pairs also defined in the name
        '''
        groups = self.getUriGroups(name) 
        if groups is None:
            return None
        _expr = groups['_expr']
        _subst = groups['_subst']
        return self.expandExpr(_expr, _subst or {})

    def getAttrName(self, s):
        #@TODO: Maybe this belongs to the factory, not the validator
        # TODO: this is pre-tep14 API from the EvaluationConfigurationNameValidator. Check usage and remove.
        names = self.getNames(s)
        if names is None: return None
        return names[0]
    
    def getDeviceName(self, name):
        #@TODO: Maybe this belongs to the factory, not the validator
        '''Obtain the fullname of the device from the attribute name'''
        from evalfactory import EvaluationFactory
        groups = self.getUriGroups(name) 
        if groups is None:
            return None
        authority = groups.get('authority')
        if authority is None:
            authority = EvaluationFactory.DEFAULT_AUTHORITY
        devname = groups.get('devname')
        if devname is None:
            devname = EvaluationFactory.DEFAULT_DEVICE
        return 'eval:%s/%s' % (authority, devname)

    def getDBName(self,s):
        #@TODO: Maybe this belongs to the factory, not the validator
        '''returns the full data base name for the given attribute name'''
        from evalfactory import EvaluationFactory
        m = self.name_re.match(s)
        if m is None:
            return None
        dbname = m.group('dbname') or EvaluationFactory.DEFAULT_DATABASE
        return "eval://db=%s"%dbname


if __name__ == '__main__':
    
    cfgval = EvaluationAttributeNameValidator()
#     print cfgval.namePattern
#     print cfgval.getNames('eval:1#')
#     print cfgval.getNames('eval:1#label')
#     print cfgval.getNames('eval://1?configuration')
#     print cfgval.getNames('eval://1?configuration=label')
    print cfgval.getNames('eval://a+b?a=2;b=3?configuration=label')
    print cfgval.isValid('eval://a+b?a=2;b=3?configuration=label')
    pass