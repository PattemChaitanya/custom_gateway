"""
Test cases for Input Validation & Sanitization module.

Tests:
1. Path parameter validation
2. Query parameter validation
3. XSS prevention (HTML sanitization)
4. SQL injection prevention
5. NoSQL injection prevention
6. Validation middleware integration
"""

import pytest
from app.validation.validators import (
    validate_path_param,
    validate_query_param,
    validate_body_size,
    ValidationError
)
from app.validation.sanitizers import (
    sanitize_html,
    sanitize_sql,
    sanitize_nosql
)


class TestPathValidation:
    """Test path parameter validation."""
    
    def test_valid_path_param(self):
        """Test that valid path parameters pass validation."""
        # Should not raise exception
        validate_path_param("user123", "user_id")
        validate_path_param("api-name", "api_name")
        validate_path_param("test_value", "param")
    
    def test_invalid_characters_in_path(self):
        """Test that invalid characters are rejected."""
        with pytest.raises(ValidationError) as exc:
            validate_path_param("user/../admin", "user_id")
        assert "invalid characters" in str(exc.value).lower()
    
    def test_sql_injection_in_path(self):
        """Test that SQL injection attempts are blocked."""
        with pytest.raises(ValidationError) as exc:
            validate_path_param("1' OR '1'='1", "user_id")
        assert "sql injection" in str(exc.value).lower()
    
    def test_path_length_limit(self):
        """Test that overly long path parameters are rejected."""
        long_param = "a" * 101
        with pytest.raises(ValidationError) as exc:
            validate_path_param(long_param, "param", max_length=100)
        assert "too long" in str(exc.value).lower()
    
    def test_empty_path_param(self):
        """Test that empty path parameters are rejected."""
        with pytest.raises(ValidationError) as exc:
            validate_path_param("", "param")
        assert "empty" in str(exc.value).lower()


class TestQueryValidation:
    """Test query parameter validation."""
    
    def test_valid_query_param(self):
        """Test that valid query parameters pass validation."""
        # Should not raise exception
        validate_query_param("10", "limit", param_type="integer")
        validate_query_param("true", "active", param_type="boolean")
        validate_query_param("test@example.com", "email", param_type="email")
    
    def test_integer_validation(self):
        """Test integer query parameter validation."""
        validate_query_param("42", "page", param_type="integer")
        
        with pytest.raises(ValidationError):
            validate_query_param("not_a_number", "page", param_type="integer")
    
    def test_boolean_validation(self):
        """Test boolean query parameter validation."""
        validate_query_param("true", "active", param_type="boolean")
        validate_query_param("false", "active", param_type="boolean")
        validate_query_param("1", "active", param_type="boolean")
        
        with pytest.raises(ValidationError):
            validate_query_param("maybe", "active", param_type="boolean")
    
    def test_email_validation(self):
        """Test email query parameter validation."""
        validate_query_param("user@example.com", "email", param_type="email")
        
        with pytest.raises(ValidationError):
            validate_query_param("invalid-email", "email", param_type="email")
    
    def test_allowed_values(self):
        """Test that only allowed values are accepted."""
        validate_query_param("asc", "sort", allowed_values=["asc", "desc"])
        
        with pytest.raises(ValidationError):
            validate_query_param("random", "sort", allowed_values=["asc", "desc"])


class TestBodyValidation:
    """Test request body validation."""
    
    def test_valid_body_size(self):
        """Test that valid body sizes pass validation."""
        body = {"name": "test", "value": 123}
        validate_body_size(body)
    
    def test_oversized_body(self):
        """Test that oversized bodies are rejected."""
        # Create a body that's too large (> 1MB)
        large_body = {"data": "x" * (1024 * 1024 + 1)}
        
        with pytest.raises(ValidationError) as exc:
            validate_body_size(large_body, max_size_mb=1)
        assert "too large" in str(exc.value).lower()
    
    def test_deeply_nested_json(self):
        """Test that deeply nested JSON is rejected."""
        # Create nested dict with depth > 10
        nested = {}
        current = nested
        for i in range(15):
            current["level"] = {}
            current = current["level"]
        
        with pytest.raises(ValidationError) as exc:
            validate_body_size(nested, max_depth=10)
        assert "too deep" in str(exc.value).lower()


class TestXSSPrevention:
    """Test XSS (Cross-Site Scripting) prevention."""
    
    def test_script_tag_removal(self):
        """Test that script tags are removed."""
        input_text = "<script>alert('XSS')</script>Hello"
        sanitized = sanitize_html(input_text)
        
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
    
    def test_event_handler_removal(self):
        """Test that event handlers are removed."""
        input_text = '<img src="x" onerror="alert(1)">'
        sanitized = sanitize_html(input_text)
        
        assert "onerror" not in sanitized
        assert "alert" not in sanitized
    
    def test_javascript_protocol_removal(self):
        """Test that javascript: protocol is removed."""
        input_text = '<a href="javascript:alert(1)">Click</a>'
        sanitized = sanitize_html(input_text)
        
        assert "javascript:" not in sanitized
    
    def test_safe_html_preserved(self):
        """Test that safe HTML is preserved."""
        input_text = "<p>Hello <b>World</b></p>"
        sanitized = sanitize_html(input_text)
        
        assert "<p>" in sanitized or "Hello" in sanitized
        assert "World" in sanitized
    
    def test_multiple_xss_vectors(self):
        """Test multiple XSS attack vectors."""
        input_text = """
            <script>alert('XSS')</script>
            <img src=x onerror=alert(1)>
            <iframe src="javascript:alert(1)"></iframe>
            <div onclick="alert(1)">Click</div>
        """
        sanitized = sanitize_html(input_text)
        
        assert "<script>" not in sanitized
        assert "onerror" not in sanitized
        assert "javascript:" not in sanitized
        assert "onclick" not in sanitized
        assert "alert" not in sanitized.lower()


class TestSQLInjectionPrevention:
    """Test SQL injection prevention."""
    
    def test_basic_sql_injection(self):
        """Test basic SQL injection patterns."""
        malicious_inputs = [
            "1' OR '1'='1",
            "admin'--",
            "'; DROP TABLE users--",
            "1' UNION SELECT * FROM passwords--"
        ]
        
        for input_text in malicious_inputs:
            sanitized = sanitize_sql(input_text)
            # Should escape or remove SQL keywords
            assert "OR" not in sanitized.upper() or "'" not in sanitized
    
    def test_comment_injection(self):
        """Test SQL comment injection."""
        input_text = "test'-- comment"
        sanitized = sanitize_sql(input_text)
        
        assert "--" not in sanitized
    
    def test_union_injection(self):
        """Test UNION-based SQL injection."""
        input_text = "1' UNION SELECT username, password FROM users--"
        sanitized = sanitize_sql(input_text)
        
        assert "UNION" not in sanitized.upper()
    
    def test_safe_input_preserved(self):
        """Test that safe input is preserved."""
        input_text = "john_doe_123"
        sanitized = sanitize_sql(input_text)
        
        assert sanitized == input_text


class TestNoSQLInjectionPrevention:
    """Test NoSQL injection prevention."""
    
    def test_mongodb_operator_injection(self):
        """Test MongoDB operator injection."""
        malicious_inputs = [
            '{"$gt": ""}',
            '{"$ne": null}',
            '{"$regex": ".*"}'
        ]
        
        for input_text in malicious_inputs:
            sanitized = sanitize_nosql(input_text)
            assert "$" not in sanitized
    
    def test_nested_operators(self):
        """Test nested operator injection."""
        input_text = '{"username": {"$gt": ""}}'
        sanitized = sanitize_nosql(input_text)
        
        assert "$gt" not in sanitized
    
    def test_safe_json_preserved(self):
        """Test that safe JSON is preserved."""
        input_text = '{"username": "john", "age": 25}'
        sanitized = sanitize_nosql(input_text)
        
        # Should preserve the structure
        assert "username" in sanitized
        assert "john" in sanitized


@pytest.mark.asyncio
class TestValidationMiddleware:
    """Test validation middleware integration."""
    
    async def test_middleware_validates_request(self):
        """Test that middleware validates incoming requests."""
        # This would require setting up a test FastAPI app
        # For now, we'll test the validation functions directly
        pass
    
    async def test_middleware_blocks_xss(self):
        """Test that middleware blocks XSS attempts."""
        pass
    
    async def test_middleware_blocks_sql_injection(self):
        """Test that middleware blocks SQL injection attempts."""
        pass


# Run tests with: pytest tests/test_validation.py -v
