# frozen_string_literal: true

module Polylib
  # Typed domain error mirroring `polylib_core::CoreError` in Ruby.
  class Error < StandardError
    attr_reader :code, :detail

    def initialize(code:, detail:)
      @code = code
      @detail = detail
      super("#{code}: #{detail}")
    end
  end

  class EmptyInputError < Error
    def initialize(detail:)
      super(code: "empty_input", detail: detail)
    end
  end

  class EmptyScoresError < Error
    def initialize(detail:)
      super(code: "empty_scores", detail: detail)
    end
  end

  class NonFiniteValueError < Error
    def initialize(detail:)
      super(code: "non_finite_value", detail: detail)
    end
  end
end
