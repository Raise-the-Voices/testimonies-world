/*
 * auth.js — client-side UX helpers for /accounts/* pages.
 *
 * Two responsibilities:
 *
 *   1. Password strength meter — listens to the first password field
 *      (any field marked `data-field-name="password"` or `"password1"`)
 *      and updates the .pw-strength bar + label.
 *
 *   2. Confirm-password match — listens to the second password field
 *      and the password_confirm field, and toggles .pw-match visibility
 *      + match-ok / match-fail classes.
 *
 * Vanilla JS, no deps. Runs once on DOMContentLoaded. The markup it
 * touches is described in auth.css; if a page doesn't render the
 * markers, this script is a no-op there.
 */
(function () {
	'use strict';

	function ready(fn) {
		if (document.readyState !== 'loading') fn();
		else document.addEventListener('DOMContentLoaded', fn);
	}

	function scorePassword(pw) {
		// Lightweight entropy estimate — not NIST-grade but useful for
		// the four buckets we surface (weak / fair / good / strong).
		if (!pw) return { label: '', score: 0 };
		var score = 0;
		if (pw.length >= 8) score += 1;
		if (pw.length >= 12) score += 1;
		if (/[A-Z]/.test(pw)) score += 1;
		if (/[a-z]/.test(pw)) score += 1;
		if (/[0-9]/.test(pw)) score += 1;
		if (/[^A-Za-z0-9]/.test(pw)) score += 1;
		if (score <= 2) return { label: 'Weak', score: 1, klass: 'weak' };
		if (score <= 4) return { label: 'Fair', score: 2, klass: 'fair' };
		if (score <= 5) return { label: 'Good', score: 3, klass: 'good' };
		return { label: 'Strong', score: 4, klass: 'strong' };
	}

	function strengthClass(klass) {
		return 'strength-' + klass;
	}

	function attachStrength(firstField) {
		var wrap = firstField.closest('.field');
		if (!wrap) return;
		var meter = wrap.querySelector('.pw-strength');
		var label = wrap.querySelector('.pw-strength-label');
		var bar = wrap.querySelector('.pw-strength-bar');
		var text = wrap.querySelector('.strength-text');
		if (!meter || !label || !bar || !text) return;

		function update() {
			var val = firstField.value || '';
			if (!val) {
				meter.classList.remove('visible');
				label.classList.remove('visible');
				bar.className = 'pw-strength-bar';
				text.textContent = '';
				return;
			}
			var r = scorePassword(val);
			meter.classList.add('visible');
			label.classList.add('visible');
			bar.className = 'pw-strength-bar ' + strengthClass(r.klass);
			text.textContent = r.label;
			text.className = 'strength-text ' + r.klass;
		}

		firstField.addEventListener('input', update);
		update();
	}

	function attachMatch(pwdField, confirmField) {
		// pwdField: the canonical password field (e.g. password2, password_confirm)
		// confirmField: the field whose value should match
		// We attach the indicator to the SAME row as confirmField.
		var wrap = confirmField.closest('.field');
		if (!wrap) return;
		var match = wrap.querySelector('.pw-match');
		var icon = match ? match.querySelector('.pw-match-icon') : null;
		var text = match ? match.querySelector('.pw-match-text') : null;
		if (!match || !icon || !text) return;

		function update() {
			var a = pwdField.value || '';
			var b = confirmField.value || '';
			if (!b) {
				match.classList.remove('visible', 'match-ok', 'match-fail');
				return;
			}
			match.classList.add('visible');
			if (a && a === b) {
				match.classList.add('match-ok');
				match.classList.remove('match-fail');
				icon.textContent = '✓';
				text.textContent = 'Passwords match.';
			} else {
				match.classList.add('match-fail');
				match.classList.remove('match-ok');
				icon.textContent = '✕';
				text.textContent = a
					? 'Passwords do not match.'
					: 'Enter your password above first.';
			}
		}

		pwdField.addEventListener('input', update);
		confirmField.addEventListener('input', update);
		update();
	}

	ready(function () {
		// Strength: pick the first field whose data-field-name is "password" or "password1"
		var forms = document.querySelectorAll('.auth-form');
		forms.forEach(function (form) {
			var pwdCandidates = form.querySelectorAll(
				'[data-field-name="password1"], [data-field-name="password"]'
			);
			if (pwdCandidates.length) attachStrength(pwdCandidates[0]);

			// Match (1): the form's second password field (password2 /
			// password_confirmation) compared against the first one.
			var pwdFields = form.querySelectorAll(
				'input[type="password"][name="password1"], input[type="password"][name="password2"], input[type="password"][name="password"], input[type="password"][name="password_confirmation"]'
			);
			if (pwdFields.length >= 2) {
				attachMatch(pwdFields[0], pwdFields[1]);
			}

			// Match (2): the optional `password_confirm` (signup-only)
			// compared against password2 (which is the allauth signup
			// password confirmation). Backend ignores this field — it's
			// a UX guard only.
			var confirm = form.querySelector(
				'input[type="password"][name="password_confirm"]'
			);
			if (confirm && pwdFields.length >= 1) {
				attachMatch(pwdFields[0], confirm);
			}
		});
	});
})();
